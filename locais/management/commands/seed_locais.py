"""Cadastro inicial conservador: recursos dependem de verificação presencial."""
from django.core.management.base import BaseCommand
from django.db import transaction

from locais.acessibilidade import PESOS
from locais.models import Local


LOCAIS = (
    {
        "nome": "Parque Carlos Alberto de Souza (Campolim)",
        "categoria": "Parque",
        "endereco": "Avenida Domingos Júlio, s/n, Parque Campolim, Sorocaba/SP",
        "latitude": "-23.525692",
        "longitude": "-47.468480",
    },
    {
        "nome": "Biblioteca Municipal Jorge Guilherme Senger",
        "categoria": "Biblioteca",
        "endereco": "Rua Ministro Coqueijo Costa, 180, Alto da Boa Vista, Sorocaba/SP",
        "latitude": "-23.481000",
        "longitude": "-47.428000",
    },
    {
        "nome": "Parque Zoológico Municipal Quinzinho de Barros",
        "categoria": "Zoológico",
        "endereco": "Rua Theodoro Kaisel, 883, Vila Hortência, Sorocaba/SP",
        "latitude": "-23.501000",
        "longitude": "-47.437000",
    },
)


LOCAIS_SIMULADOS = (
    {
        "nome": "[SIMULADO] Café Acolher",
        "categoria": "Cafeteria",
        "endereco": "Endereço fictício de demonstração, Centro, Sorocaba/SP",
        "latitude": "-23.501500", "longitude": "-47.458000",
        "recursos": {
            "rampa": "atendido", "banheiro_adaptado": "atendido",
            "vaga_acessivel": "atendido", "elevador": "nao_aplicavel",
            "piso_tatil": "atendido", "recurso_auditivo": "atendido",
        },
    },
    {
        "nome": "[SIMULADO] Clínica Bem Viver",
        "categoria": "Clínica",
        "endereco": "Endereço fictício de demonstração, Campolim, Sorocaba/SP",
        "latitude": "-23.520000", "longitude": "-47.470000",
        "recursos": {
            "rampa": "atendido", "banheiro_adaptado": "atendido",
            "vaga_acessivel": "atendido", "elevador": "atendido",
            "piso_tatil": "atendido", "recurso_auditivo": "nao_atendido",
        },
    },
    {
        "nome": "[SIMULADO] Restaurante Sabor da Vila",
        "categoria": "Restaurante",
        "endereco": "Endereço fictício de demonstração, Santa Rosália, Sorocaba/SP",
        "latitude": "-23.480000", "longitude": "-47.450000",
        "recursos": {
            "rampa": "atendido", "banheiro_adaptado": "atendido",
            "vaga_acessivel": "nao_atendido", "elevador": "nao_aplicavel",
            "piso_tatil": "nao_atendido", "recurso_auditivo": "nao_atendido",
        },
    },
    {
        "nome": "[SIMULADO] Mercado do Bairro",
        "categoria": "Mercado",
        "endereco": "Endereço fictício de demonstração, Vila Hortência, Sorocaba/SP",
        "latitude": "-23.510000", "longitude": "-47.440000",
        "recursos": {
            "rampa": "atendido", "banheiro_adaptado": "nao_atendido",
            "vaga_acessivel": "nao_atendido", "elevador": "nao_aplicavel",
            "piso_tatil": "nao_atendido", "recurso_auditivo": "nao_atendido",
        },
    },
)


class Command(BaseCommand):
    help = "Cadastra locais iniciais de Sorocaba sem sobrescrever registros existentes."

    @transaction.atomic
    def handle(self, *args, **options):
        # Serializa execuções concorrentes no PostgreSQL, sem alterar o schema.
        from django.db import connection

        if connection.vendor == "postgresql":
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_xact_lock(%s)", [736334562])

        criados = existentes = 0
        for dados in (*LOCAIS, *LOCAIS_SIMULADOS):
            identidade = {
                "nome__iexact": dados["nome"],
                "endereco__iexact": dados["endereco"],
                "cidade": "Sorocaba",
                "estado": "SP",
            }
            defaults = {
                "localizacao_confirmada": True,
                "descricao": (
                    "Cadastro inicial. Coordenadas aproximadas; confirme a entrada antes "
                    "do deslocamento. Recursos de acessibilidade ainda não verificados."
                ),
                "recursos": {recurso: "nao_informado" for recurso in PESOS},
                **dados,
            }
            if dados in LOCAIS_SIMULADOS:
                defaults["descricao"] = (
                    "DEMONSTRAÇÃO: estabelecimento particular fictício. Endereço, "
                    "coordenadas e recursos simulados para testar a interface e a nota. "
                    "Não representa um local real e não deve ser usado para deslocamentos."
                )
            Local(**defaults).full_clean()
            # Não sobrescreve revisões, recursos ou coordenadas de cadastros existentes.
            # Tolera duplicatas legadas sem inserir outra cópia.
            if Local.objects.filter(**identidade).exists():
                existentes += 1
                continue
            _, criado = Local.objects.get_or_create(**identidade, defaults=defaults)
            criados += int(criado)
            existentes += int(not criado)

        self.stdout.write(self.style.SUCCESS(
            f"Locais criados: {criados}. Locais já existentes: {existentes}."
        ))
