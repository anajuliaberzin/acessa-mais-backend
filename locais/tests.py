from io import BytesIO
from tempfile import TemporaryDirectory
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings, RequestFactory
from django.contrib import admin
from rest_framework.test import APIClient
from PIL import Image
from .models import Local, Ocorrencia, Avaliacao, Favorito, HistoricoOcorrencia
from .acessibilidade import PESOS, calcular_acessibilidade
from .admin import LocalForm, LocalAdmin


def recursos(estado='atendido'):
    return {nome: estado for nome in PESOS}


class AcessibilidadeTests(TestCase):
    def test_notas_e_classificacoes(self):
        for atendidos, esperado, classe in [
            ([], 0, 'baixa acessibilidade'),
            (['rampa', 'banheiro_adaptado'], 40, 'acessibilidade parcial'),
            (['rampa', 'banheiro_adaptado', 'elevador', 'piso_tatil'], 70, 'boa acessibilidade'),
            (list(PESOS), 100, 'alta acessibilidade'),
        ]:
            with self.subTest(esperado=esperado):
                dados = recursos('nao_atendido')
                dados.update({nome: 'atendido' for nome in atendidos})
                resultado = calcular_acessibilidade(dados)
                self.assertEqual(resultado['nota'], esperado)
                self.assertEqual(resultado['classificacao'], classe)

    def test_elevador_nao_aplicavel_nao_penaliza_terreo(self):
        dados = recursos()
        dados['elevador'] = 'nao_aplicavel'
        resultado = calcular_acessibilidade(dados)
        self.assertEqual(resultado['nota'], 100)
        self.assertEqual(resultado['pontos_aplicaveis'], 85)

    def test_normalizacao_fracionaria(self):
        dados = recursos()
        dados['elevador'] = 'nao_aplicavel'
        dados['piso_tatil'] = 'nao_atendido'
        self.assertAlmostEqual(calcular_acessibilidade(dados)['nota'], 70 / 85 * 100)

    def test_dados_insuficientes_nao_produzem_nota_ficticia(self):
        for dados in ({}, recursos('nao_aplicavel'), recursos('nao_informado')):
            self.assertIsNone(calcular_acessibilidade(dados)['nota'])


class ApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model()
        cls.usuario = users.objects.create_user(username='cidadao', password='senha-teste')
        cls.outro = users.objects.create_user(username='outro', password='senha-teste')
        cls.gestor = users.objects.create_user(username='gestor', password='senha-teste', is_staff=True)
        cls.local = Local.objects.create(nome='Biblioteca', categoria='cultura', endereco='Centro, Sorocaba/SP',
                                        localizacao_confirmada=True, recursos=recursos(), latitude=-23.5, longitude=-47.4)
        cls.pendente = Local.objects.create(nome='Não revisado', categoria='cultura', endereco='Revisar')

    def setUp(self):
        self.client = APIClient()

    def login(self, usuario=None):
        resposta = self.client.post('/api/auth/login/', {'username': (usuario or self.usuario).username, 'password': 'senha-teste'}, format='json')
        self.assertEqual(resposta.status_code, 200)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + resposta.data['access'])

    def payload(self, **kwargs):
        return {'endereco': 'Rua da Penha, Sorocaba/SP', 'tipoProblema': 'obstaculo_na_via',
                'descricao': 'Obstáculo bloqueia a passagem na calçada.', 'confirmadoSorocaba': True, **kwargs}

    def criar_ocorrencia(self, usuario=None):
        return Ocorrencia.objects.create(autor=usuario or self.usuario, endereco='Centro',
                                        tipo_problema='obstaculo_na_via', descricao='Obstáculo na calçada')

    def test_consultas_publicas_e_revisao_geografica(self):
        for url in ['/api/locais/', '/api/locais/filtros/', '/api/locais/mapa/', f'/api/locais/{self.local.pk}/', f'/api/locais/{self.local.pk}/avaliacoes/']:
            self.assertEqual(self.client.get(url).status_code, 200, url)
        resposta = self.client.get('/api/locais/')
        self.assertEqual(resposta.data['count'], 1)
        self.assertEqual(resposta.data['results'][0]['acessibilidade']['nota'], 100)
        self.assertEqual(self.client.get(f'/api/locais/{self.pendente.pk}/').status_code, 404)

    def test_busca_filtros_e_mapa(self):
        for filtros in [{'nome': 'BIBLIO'}, {'categoria': 'CULTURA'}, {'recursos': 'rampa,elevador'}, {'necessidade': 'visual'}, {'bbox': '-48,-24,-47,-23'}]:
            resposta = self.client.get('/api/locais/', filtros)
            self.assertEqual(resposta.status_code, 200)
            self.assertEqual(resposta.data['count'], 1)
        self.assertEqual(self.client.get('/api/locais/', {'nome': 'inexistente'}).data['count'], 0)
        self.assertEqual(self.client.get('/api/locais/mapa/', {'bbox': '-46,-24,-45,-23'}).data['count'], 0)
        for filtros in [{'bbox': 'nan,0,1,2'}, {'bbox': '1,2'}, {'recursos': 'inventado'}, {'necessidade': 'inventado'}]:
            self.assertEqual(self.client.get('/api/locais/', filtros).status_code, 400)

    def test_destaques_excluem_locais_sem_nota(self):
        Local.objects.create(nome='Sem avaliação de recursos', categoria='cultura', endereco='Sorocaba', localizacao_confirmada=True)
        self.assertEqual(self.client.get('/api/locais/').data['count'], 2)
        self.assertEqual(self.client.get('/api/locais/', {'ordenacao': 'acessibilidade'}).data['count'], 1)

    def test_reporte_exige_jwt(self):
        self.assertEqual(self.client.post('/api/ocorrencias/', self.payload()).status_code, 401)

    def test_reporte_protocolo_autor_e_historico(self):
        self.login()
        resposta = self.client.post('/api/ocorrencias/', self.payload(autor=self.outro.pk, status='resolvida', latitude='-23.501234', longitude='-47.456789'), format='multipart')
        self.assertEqual(resposta.status_code, 201, resposta.data)
        ocorrencia = Ocorrencia.objects.get(pk=resposta.data['id'])
        self.assertEqual(ocorrencia.autor, self.usuario)
        self.assertEqual(ocorrencia.status, 'em_analise')
        self.assertTrue(resposta.data['protocolo'].startswith('AC-'))
        self.assertEqual(len(resposta.data['historico']), 1)
        self.assertEqual(resposta.json()['latitude'], -23.501234)

    def test_validacoes_reporte(self):
        self.login()
        for payload in [self.payload(confirmadoSorocaba=False), self.payload(descricao='curta'), self.payload(latitude='-23.5'), self.payload(tipoProblema='invalido')]:
            self.assertEqual(self.client.post('/api/ocorrencias/', payload, format='json').status_code, 400)

    def test_foto_validada_e_privada(self):
        with TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            self.login()
            imagem = BytesIO()
            Image.new('RGB', (3, 3)).save(imagem, format='PNG')
            resposta = self.client.post('/api/ocorrencias/', self.payload(foto=SimpleUploadedFile('foto.png', imagem.getvalue(), content_type='image/png')), format='multipart')
            self.assertEqual(resposta.status_code, 201, resposta.data)
            url = resposta.data['fotoUrl']
            resposta_foto = self.client.get(url)
            self.assertEqual(resposta_foto.status_code, 200)
            resposta_foto.close()
            self.login(self.outro)
            self.assertEqual(self.client.get(url).status_code, 404)
            self.client.credentials()
            self.assertEqual(self.client.get(url).status_code, 401)
            self.login()
            falsa = SimpleUploadedFile('falsa.png', b'nao e imagem', content_type='image/png')
            self.assertEqual(self.client.post('/api/ocorrencias/', self.payload(foto=falsa), format='multipart').status_code, 400)

    def test_ocorrencias_isoladas_por_autor(self):
        minha = self.criar_ocorrencia()
        outra = self.criar_ocorrencia(self.outro)
        self.login()
        resposta = self.client.get('/api/ocorrencias/')
        self.assertEqual([x['id'] for x in resposta.data['results']], [minha.pk])
        self.assertEqual(self.client.get(f'/api/ocorrencias/{outra.pk}/').status_code, 404)




    def test_perfil_persistencia_e_sem_elevacao_privilegio(self):
        self.login()
        resposta = self.client.patch('/api/me/', {'nome': 'Meu nome', 'preferencias': ['cadeirante'], 'gestor': True}, format='json')
        self.assertEqual(resposta.status_code, 200, resposta.data)
        self.assertEqual(self.client.get('/api/me/').data['preferencias'], ['cadeirante'])
        self.assertFalse(self.client.get('/api/me/').data['gestor'])
        self.assertEqual(self.client.patch('/api/me/', {'preferencias': ['invalida']}, format='json').status_code, 400)
        self.assertEqual(self.client.patch('/api/me/', {'preferencias': [['cadeirante']]}, format='json').status_code, 400)
        self.login(self.outro)
        self.assertEqual(self.client.get('/api/me/').data['preferencias'], [])

    def test_favoritos_idempotentes_e_isolados(self):
        self.login()
        url = f'/api/me/favoritos/{self.local.pk}/'
        self.assertEqual(self.client.put(url).status_code, 201)
        self.assertEqual(self.client.put(url).status_code, 200)
        self.assertEqual(Favorito.objects.count(), 1)
        self.assertEqual(self.client.get('/api/me/favoritos/').data['count'], 1)
        self.login(self.outro)
        self.assertEqual(self.client.get('/api/me/favoritos/').data['count'], 0)
        self.client.delete(url)
        self.assertEqual(Favorito.objects.count(), 1)
        self.login()
        self.assertEqual(self.client.delete(url).status_code, 204)

    def test_avaliacao_subjetiva_nao_altera_nota_acessibilidade(self):
        self.login()
        url = f'/api/locais/{self.local.pk}/avaliacoes/'
        resposta = self.client.post(url, {'nota': 1, 'comentario': 'Minha opinião'}, format='json')
        self.assertEqual(resposta.status_code, 201, resposta.data)
        self.assertEqual(self.client.post(url, {'nota': 2, 'comentario': 'Duplicada'}, format='json').status_code, 400)
        detalhe = self.client.get(f'/api/locais/{self.local.pk}/').data
        self.assertEqual(detalhe['acessibilidade']['nota'], 100)
        self.assertEqual(detalhe['media_avaliacoes'], 1)
        self.assertEqual(self.client.get('/api/me/avaliacoes/').data['count'], 1)
        self.assertEqual(self.client.get('/api/me/contribuicoes/').data['avaliacoes'], 1)
        self.login(self.outro)
        self.assertEqual(self.client.delete(f'/api/me/avaliacoes/{resposta.data["id"]}/').status_code, 404)

    def test_admin_cadastra_aplicabilidade_e_bloqueia_outra_cidade(self):
        dados = {'nome': 'Térreo', 'categoria': 'COMÉRCIO', 'endereco': 'Sorocaba', 'cidade': 'Sorocaba', 'estado': 'SP', 'localizacao_confirmada': True, **recursos()}
        dados['elevador'] = 'nao_aplicavel'
        form = LocalForm(data=dados)
        self.assertTrue(form.is_valid(), form.errors)
        local = form.save()
        self.assertEqual(local.recursos['elevador'], 'nao_aplicavel')
        self.assertEqual(local.categoria, 'comércio')
        dados['cidade'] = 'Votorantim'
        self.assertFalse(LocalForm(data=dados).is_valid())

    def test_admin_exibe_os_seis_criterios(self):
        request = RequestFactory().get('/admin/locais/local/add/')
        request.user = self.gestor
        form = LocalAdmin(Local, admin.site).get_form(request)
        self.assertTrue(set(PESOS).issubset(form.base_fields))
