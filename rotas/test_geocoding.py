import json
from unittest.mock import MagicMock, patch
from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APITestCase
from .services.geocoding_service import buscar_enderecos
from .services.routing_service import RoutingError


@override_settings(ROUTING_API_KEY='chave-teste')
class EnderecosTests(APITestCase):
    def setUp(self):
        cache.clear()

    def feature(self, cidade='Sorocaba', coords=None):
        return {'properties': {'locality': cidade, 'region_a': 'SP', 'country_a': 'BRA', 'label': 'Rua da Penha, Sorocaba'},
                'geometry': {'type': 'Point', 'coordinates': coords or [-47.45, -23.50]}}

    @patch('rotas.services.geocoding_service.build_opener')
    def test_busca_publica_filtra_municipio_e_reutiliza_cache(self, opener):
        resposta = MagicMock()
        resposta.read.return_value = json.dumps({'features':[self.feature(),self.feature('Votorantim')]}).encode()
        opener.return_value.open.return_value.__enter__.return_value = resposta
        resultado = self.client.get('/api/rotas/enderecos/', {'q':'Rua da Penha'})
        self.assertEqual(resultado.status_code, 200)
        self.assertEqual(len(resultado.data['results']), 1)
        self.assertEqual(resultado.data['results'][0]['latitude'], -23.5)
        self.client.get('/api/rotas/enderecos/', {'q':'Rua da Penha'})
        self.assertEqual(opener.call_count, 1)
        req = opener.return_value.open.call_args.args[0]
        self.assertNotIn('chave-teste', req.full_url)
        self.assertEqual(req.get_header('Authorization'), 'chave-teste')

    @patch('rotas.services.geocoding_service.build_opener')
    def test_rejeita_resposta_invalida(self, opener):
        resposta = MagicMock()
        resposta.read.return_value = json.dumps({'features':[self.feature(coords=[999,0])]}).encode()
        opener.return_value.open.return_value.__enter__.return_value = resposta
        resultado = self.client.get('/api/rotas/enderecos/', {'q':'Rua da Penha'})
        self.assertEqual(resultado.status_code, 502)

    @override_settings(ROUTING_API_KEY='')
    def test_informa_ausencia_de_configuracao(self):
        resultado = self.client.get('/api/rotas/enderecos/', {'q':'Rua da Penha'})
        self.assertEqual(resultado.status_code, 503)

    @patch('rotas.services.geocoding_service.build_opener')
    def test_valida_texto_sem_chamar_provedor(self, opener):
        self.assertEqual(self.client.get('/api/rotas/enderecos/', {'q':'ab'}).status_code,400)
        opener.assert_not_called()
