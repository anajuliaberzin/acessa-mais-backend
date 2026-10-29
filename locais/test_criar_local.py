from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from .models import Local
from .acessibilidade import PESOS


class CriarLocalTests(APITestCase):
    def setUp(self):
        self.dados = dict(nome='Teste', categoria='Parque', endereco='Sorocaba/SP',
                          latitude='-23.500000', longitude='-47.450000',
                          localizacao_confirmada=True,
                          recursos={r: 'atendido' for r in PESOS})

    def test_permissoes(self):
        self.assertEqual(self.client.post('/api/gestao/locais/', self.dados, format='json').status_code, 401)
        staff = get_user_model().objects.create_user(username='gestor', is_staff=True)
        self.client.force_authenticate(staff)
        self.assertEqual(self.client.post('/api/gestao/locais/', self.dados, format='json').status_code, 403)
        self.assertFalse(Local.objects.exists())

    def test_cria_local_publico_com_nota_e_valida_recursos_e_cidade(self):
        admin = get_user_model().objects.create_user(username='admin', is_superuser=True, is_staff=True)
        self.client.force_authenticate(admin)
        for alteracao in ({'cidade': 'Votorantim'}, {'recursos': {'rampa': 'sim'}},
                          {'localizacao_confirmada': False}, {'latitude': '100'}):
            response = self.client.post('/api/gestao/locais/', {**self.dados, **alteracao}, format='json')
            self.assertEqual(response.status_code, 400)
        response = self.client.post('/api/gestao/locais/', self.dados, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['acessibilidade']['nota'], 100)
        self.assertEqual(self.client.get('/api/locais/').data['count'], 1)
