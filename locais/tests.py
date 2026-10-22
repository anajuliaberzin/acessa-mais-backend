from io import BytesIO
from tempfile import TemporaryDirectory
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings, RequestFactory
from django.contrib import admin
from rest_framework.test import APIClient
from PIL import Image
from .models import Local, Avaliacao
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
