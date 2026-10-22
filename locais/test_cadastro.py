from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APITestCase
from .models import Perfil


class CadastroTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.dados = {'nome': 'Pessoa Teste', 'username': 'pessoa', 'email': 'pessoa@example.com',
                      'password': 'Mosaico!72Verde', 'password_confirmation': 'Mosaico!72Verde'}

    def test_cria_cidadao_com_senha_protegida_perfil_e_login_jwt(self):
        resposta = self.client.post('/api/auth/register/', {**self.dados, 'is_staff': True, 'is_superuser': True}, format='json')
        self.assertEqual(resposta.status_code, 201)
        self.assertNotIn('password', resposta.data)
        usuario = get_user_model().objects.get(username='pessoa')
        self.assertTrue(usuario.check_password(self.dados['password']))
        self.assertFalse(usuario.is_staff)
        self.assertFalse(usuario.is_superuser)
        self.assertEqual(Perfil.objects.get(usuario=usuario).nome, 'Pessoa Teste')
        login = self.client.post('/api/auth/login/', {'username': 'pessoa', 'password': self.dados['password']}, format='json')
        self.assertEqual(login.status_code, 200)
        self.assertIn('access', login.data)

    def test_recusa_senha_fraca_e_confirmacao_diferente_sem_criar_usuario(self):
        for senha, confirmacao in [('12345678', '12345678'), ('Mosaico!72Verde', 'outra')]:
            resposta = self.client.post('/api/auth/register/', {**self.dados, 'password': senha, 'password_confirmation': confirmacao}, format='json')
            self.assertEqual(resposta.status_code, 400)
        self.assertFalse(get_user_model().objects.exists())

    def test_usuario_duplicado_e_email_invalido(self):
        self.client.post('/api/auth/register/', self.dados, format='json')
        resposta = self.client.post('/api/auth/register/', self.dados, format='json')
        self.assertEqual(resposta.status_code, 400)
        self.assertIn('username', resposta.data)
        resposta = self.client.post('/api/auth/register/', {**self.dados, 'username':'novo', 'email':'invalido'}, format='json')
        self.assertEqual(resposta.status_code, 400)
        self.assertEqual(get_user_model().objects.count(), 1)
