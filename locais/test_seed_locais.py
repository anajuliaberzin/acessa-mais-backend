from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from locais.acessibilidade import PESOS
from locais.management.commands.seed_locais import LOCAIS, LOCAIS_SIMULADOS
from locais.models import Local


class SeedLocaisTests(TestCase):
    def test_reexecucao_preserva_revisoes_e_listagem_publica(self):
        output = StringIO()
        call_command('seed_locais', stdout=output)
        self.assertIn('Locais criados: 7', output.getvalue())
        local = Local.objects.get(nome=LOCAIS[0]['nome'])
        local.recursos = {recurso: 'atendido' for recurso in PESOS}
        local.descricao = 'Cadastro revisado pela equipe'
        local.save()
        output = StringIO()
        call_command('seed_locais', stdout=output)
        self.assertIn('Locais criados: 0. Locais já existentes: 7.', output.getvalue())
        self.assertEqual(Local.objects.count(), 7)
        local.refresh_from_db()
        self.assertEqual(local.descricao, 'Cadastro revisado pela equipe')
        self.assertTrue(all(valor == 'atendido' for valor in local.recursos.values()))
        response = self.client.get('/api/locais/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['count'], 7)
        for item in response.json()['results']:
            self.assertIsNotNone(item['latitude'])
            self.assertIsNotNone(item['longitude'])
            if not item['nome'].startswith('[SIMULADO]'):
                self.assertEqual(item['acessibilidade']['nota'], 100 if item['id'] == local.pk else None)

    def test_simulados_aparecem_no_ranking_com_notas_calculadas(self):
        call_command('seed_locais', stdout=StringIO())
        response = self.client.get('/api/locais/', {'ordenacao': 'acessibilidade'})
        self.assertEqual(response.status_code, 200)
        itens = response.json()['results']
        self.assertEqual(len(itens), len(LOCAIS_SIMULADOS))
        for item, nota in zip(itens, (100, 85, 40 / 85 * 100, 20 / 85 * 100)):
            self.assertTrue(item['nome'].startswith('[SIMULADO]'))
            self.assertAlmostEqual(item['acessibilidade']['nota'], nota)
            self.assertTrue(item['acessibilidade']['cadastro_completo'])
