"""Create clearly marked, repeatable dashboard data for a non-production environment."""
import os
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from locais.acessibilidade import PESOS
from locais.models import Avaliacao, HistoricoOcorrencia, Local, Ocorrencia, Perfil


LOCAL_CONFIGS = (
    ("Café", {"rampa", "banheiro_adaptado", "vaga_acessivel", "elevador", "piso_tatil", "recurso_auditivo"}),
    ("Clínica", {"rampa", "banheiro_adaptado", "vaga_acessivel", "elevador", "piso_tatil"}),
    ("Mercado", {"rampa", "banheiro_adaptado", "vaga_acessivel"}),
    ("Centro comunitário", {"rampa"}),
    ("Restaurante", {"rampa", "banheiro_adaptado", "vaga_acessivel", "elevador", "piso_tatil", "recurso_auditivo"}),
    ("Farmácia", {"rampa", "banheiro_adaptado", "vaga_acessivel", "elevador", "piso_tatil"}),
    ("Biblioteca", {"rampa", "banheiro_adaptado", "vaga_acessivel"}),
    ("Parque", {"rampa"}),
    ("Padaria", {"rampa", "banheiro_adaptado", "vaga_acessivel", "elevador", "piso_tatil", "recurso_auditivo"}),
    ("Escola", {"rampa", "banheiro_adaptado", "vaga_acessivel", "elevador", "piso_tatil"}),
    ("Praça", {"rampa", "banheiro_adaptado", "vaga_acessivel"}),
    ("Terminal", {"rampa"}),
)

AVALIADORES_DEMO = 8
NOTAS_BASE_DEMO = (5, 4, 3, 2, 5, 4, 3, 2, 5, 4, 3, 2)

TIPOS_DEMO = (
    "obstaculo_na_via",
    "calcada_em_mau_estado",
    "rampa_ausente_ou_inadequada",
    "vaga_acessivel_indisponivel",
    "elevador_indisponivel",
    "piso_tatil_ausente_ou_danificado",
    "banheiro_nao_adaptado",
    "outro",
)

OCORRENCIAS_DEMO = (
    (0, "em_analise"),
    (0, "em_analise"),
    (1, "em_analise"),
    (1, "em_analise"),
    (2, "em_analise"),
    (2, "em_analise"),
    (3, "confirmada"),
    (3, "confirmada"),
    (4, "confirmada"),
    (5, "confirmada"),
    (6, "confirmada"),
    (7, "confirmada"),
    (8, "resolvida"),
    (9, "resolvida"),
    (10, "resolvida"),
    (11, "resolvida"),
    (13, "resolvida"),
    (15, "resolvida"),
)

class Command(BaseCommand):
    help = "Popula os gráficos com dados de demonstração em homologação."

    def add_arguments(self, parser):
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Confirma a criação de dados sintéticos e claramente identificados.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        allowed = os.getenv("ALLOW_DEMO_DATA_SEEDING", "").strip().lower()
        if allowed not in {"1", "true", "yes"}:
            raise CommandError(
                "Execução bloqueada. Defina ALLOW_DEMO_DATA_SEEDING=true somente "
                "no serviço de homologação."
            )
        if not options["confirm"]:
            raise CommandError(
                "Confirme a carga de demonstração executando o comando com --confirm."
            )

        usuarios = [
            self._get_demo_user("demo_dashboard_autor", "DEMONSTRAÇÃO - autor"),
            *(
                self._get_demo_user(
                    f"demo_dashboard_avaliador_{indice:02}",
                    f"DEMONSTRAÇÃO - avaliador {indice:02}",
                )
                for indice in range(1, AVALIADORES_DEMO + 1)
            ),
        ]
        autor = usuarios[0]
        avaliadores = usuarios[1:]
        locais = self._get_demo_locais()
        agora = timezone.now().replace(hour=12, minute=0, second=0, microsecond=0)

        self._criar_ocorrencias(autor, agora)
        self._criar_avaliacoes(locais, avaliadores)

        self.stdout.write(self.style.SUCCESS(
            "Dados de demonstração sincronizados: "
            f"{len(OCORRENCIAS_DEMO)} ocorrências, "
            f"{AVALIADORES_DEMO * len(locais)} avaliações e "
            f"{len(locais)} locais. Nenhum registro foi removido."
        ))

    def _get_demo_user(self, username, nome):
        user_model = get_user_model()
        email = f"{username}@example.invalid"
        usuario, criado = user_model.objects.get_or_create(
            username=username,
            defaults={
                "email": email,
                "is_active": False,
                "is_staff": False,
                "is_superuser": False,
            },
        )
        if criado:
            usuario.set_unusable_password()
            usuario.save(update_fields=["password"])
        elif (
            usuario.email != email
            or usuario.is_active
            or usuario.is_staff
            or usuario.is_superuser
            or usuario.has_usable_password()
        ):
            raise CommandError(
                f"O usuário reservado {username} já existe com dados não demonstrativos."
            )
        Perfil.objects.get_or_create(usuario=usuario, defaults={"nome": nome})
        return usuario

    def _get_demo_locais(self):
        locais = []
        for indice, (categoria, atendidos) in enumerate(LOCAL_CONFIGS, start=1):
            nome = f"[DEMONSTRAÇÃO] Local {indice:02} - {categoria}"
            endereco = f"[DEMONSTRAÇÃO] Endereço fictício {indice:02}, Sorocaba/SP"
            descricao = (
                "DEMONSTRAÇÃO: local e endereço fictícios, criados apenas para testar "
                "o painel de homologação. Não use para deslocamentos."
            )
            local = Local.objects.filter(nome=nome, endereco=endereco).first()
            if local is None:
                local = Local(nome=nome, endereco=endereco)
            elif not local.descricao.startswith("DEMONSTRAÇÃO:"):
                raise CommandError(
                    f"O local reservado {nome} já existe e não está marcado como demonstração."
                )
            local.categoria = categoria
            local.descricao = descricao
            local.cidade = "Sorocaba"
            local.estado = "SP"
            local.localizacao_confirmada = True
            local.recursos = {
                recurso: "atendido" if recurso in atendidos else "nao_atendido"
                for recurso in PESOS
            }
            local.save()
            locais.append(local)
        return locais

    def _criar_ocorrencias(self, autor, agora):
        for indice, (dias_atras, status) in enumerate(OCORRENCIAS_DEMO, start=1):
            protocolo = f"AC-DEMO-P-{indice:03}"
            criado_em = agora - timedelta(days=dias_atras)
            dados = {
                "autor": autor,
                "endereco": f"[DEMONSTRAÇÃO] Endereço fictício {indice:02}, Sorocaba/SP",
                "tipo_problema": TIPOS_DEMO[(indice - 1) % len(TIPOS_DEMO)],
                "descricao": (
                    f"[DEMONSTRAÇÃO] Relato sintético {indice:02}, criado para testar "
                    "os gráficos de homologação. Não representa uma ocorrência real."
                ),
                "status": status,
            }
            ocorrencia, criada = Ocorrencia.objects.get_or_create(
                protocolo=protocolo,
                defaults=dados,
            )
            if not criada and ocorrencia.autor_id != autor.pk:
                raise CommandError(
                    f"O protocolo reservado {protocolo} já pertence a outro usuário."
                )
            for campo, valor in dados.items():
                setattr(ocorrencia, campo, valor)
            ocorrencia.save()
            Ocorrencia.objects.filter(pk=ocorrencia.pk).update(
                created_at=criado_em,
                updated_at=criado_em,
            )

            self._sincronizar_historico(ocorrencia, autor, status, criado_em)

    def _sincronizar_historico(self, ocorrencia, responsavel, status, criado_em):
        transicoes = [("em_analise", criado_em)]
        if status in {"confirmada", "resolvida"}:
            transicoes.append(("confirmada", criado_em + timedelta(hours=5)))
        if status == "resolvida":
            transicoes.append(("resolvida", criado_em + timedelta(days=3)))

        for estado, data in transicoes:
            justificativa = f"DEMONSTRAÇÃO: transição sintética para {estado}."
            historico, _ = HistoricoOcorrencia.objects.get_or_create(
                ocorrencia=ocorrencia,
                responsavel=responsavel,
                status=estado,
                justificativa=justificativa,
            )
            HistoricoOcorrencia.objects.filter(pk=historico.pk).update(created_at=data)

    def _criar_avaliacoes(self, locais, avaliadores):
        for indice_avaliador, avaliador in enumerate(avaliadores):
            for indice_local, local in enumerate(locais):
                nota = max(
                    1,
                    min(5, NOTAS_BASE_DEMO[indice_local] + (-1, 0, 1)[indice_avaliador % 3]),
                )
                comentario = (
                    "DEMONSTRAÇÃO: avaliação fictícia para popular os gráficos de homologação."
                )
                avaliacao, criada = Avaliacao.objects.get_or_create(
                    local=local,
                    autor=avaliador,
                    defaults={"nota": nota, "comentario": comentario},
                )
                if not criada and not avaliacao.comentario.startswith("DEMONSTRAÇÃO:"):
                    raise CommandError(
                        f"A avaliação reservada do local {local.pk} não é demonstrativa."
                    )
                avaliacao.nota = nota
                avaliacao.comentario = comentario
                avaliacao.save(update_fields=["nota", "comentario"])
