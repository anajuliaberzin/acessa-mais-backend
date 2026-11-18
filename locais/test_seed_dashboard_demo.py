import os
from io import StringIO
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.management import call_command, CommandError
from django.test import TestCase
from rest_framework.test import APIClient

from locais.models import Avaliacao, HistoricoOcorrencia, Local, Ocorrencia, Perfil


class SeedDashboardDemoTests(TestCase):
    def test_requires_environment_gate_and_confirmation(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ALLOW_DEMO_DATA_SEEDING", None)
            with self.assertRaises(CommandError):
                call_command("seed_dashboard_demo", confirm=True)

        with mock.patch.dict(os.environ, {"ALLOW_DEMO_DATA_SEEDING": "true"}):
            with self.assertRaises(CommandError):
                call_command("seed_dashboard_demo")

    def test_seeds_all_dashboard_charts_idempotently_without_real_users(self):
        with mock.patch.dict(os.environ, {"ALLOW_DEMO_DATA_SEEDING": "true"}):
            call_command("seed_dashboard_demo", confirm=True, stdout=StringIO())
            expected_counts = (
                Local.objects.count(),
                Ocorrencia.objects.count(),
                HistoricoOcorrencia.objects.count(),
                Avaliacao.objects.count(),
                Perfil.objects.count(),
            )
            self.assertEqual(expected_counts[:2], (12, 18))
            self.assertEqual(expected_counts[3:], (96, 9))
            self.assertTrue(all(
                local.nome.startswith("[DEMONSTRAÇÃO]")
                and "fictício" in local.descricao
                for local in Local.objects.all()
            ))
            self.assertTrue(all(
                not usuario.is_active
                and not usuario.is_staff
                and not usuario.is_superuser
                and not usuario.has_usable_password()
                for usuario in get_user_model().objects.all()
            ))

            call_command("seed_dashboard_demo", confirm=True, stdout=StringIO())
            self.assertEqual(
                (
                    Local.objects.count(),
                    Ocorrencia.objects.count(),
                    HistoricoOcorrencia.objects.count(),
                    Avaliacao.objects.count(),
                    Perfil.objects.count(),
                ),
                expected_counts,
            )

        gestor = get_user_model().objects.create_superuser(
            username="gestor-indicadores",
            email="gestor@example.com",
            password="Mosaico!72Verde",
        )
        client = APIClient()
        client.force_authenticate(gestor)
        resposta = client.get("/api/gestao/indicadores/")
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.data["total_ocorrencias"], 18)
        self.assertEqual(len(resposta.data["por_tipo"]), 8)
        self.assertEqual(len(resposta.data["evolucao"]), 14)
        self.assertEqual(
            {item["status"]: item["total"] for item in resposta.data["por_status"]},
            {"em_analise": 6, "confirmada": 6, "resolvida": 6},
        )
        self.assertEqual(resposta.data["locais_com_nota"], 12)
        self.assertEqual(
            {item["classificacao"]: item["total"] for item in resposta.data["por_acessibilidade"]},
            {
                "baixa acessibilidade": 3,
                "acessibilidade parcial": 3,
                "boa acessibilidade": 3,
                "alta acessibilidade": 3,
            },
        )
        self.assertEqual(resposta.data["total_avaliacoes"], 96)
        self.assertTrue(all(item["total"] > 0 for item in resposta.data["avaliacoes_por_nota"]))
        self.assertEqual(len(resposta.data["locais_mais_bem_avaliados"]), 5)
        self.assertEqual(len(resposta.data["locais_menos_bem_avaliados"]), 5)
