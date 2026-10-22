from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from uuid import uuid4
from .validators import validar_recursos, validar_preferencias


class Local(models.Model):
    nome = models.CharField(max_length=255)
    categoria = models.CharField(max_length=100)
    endereco = models.CharField(max_length=255)
    descricao = models.TextField(blank=True, default="")
    cidade = models.CharField(max_length=40, default='Sorocaba', choices=[('Sorocaba', 'Sorocaba')])
    estado = models.CharField(max_length=2, default='SP', choices=[('SP', 'SP')])
    # Cadastros anteriores precisam ser revisados antes de entrar na consulta pública.
    localizacao_confirmada = models.BooleanField(default=False, help_text='Confirme que o endereço pertence a Sorocaba/SP.')
    recursos = models.JSONField(default=dict, blank=True, validators=[validar_recursos])
    latitude = models.DecimalField(
        max_digits=8,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nome"]
        verbose_name = "Local"
        verbose_name_plural = "Locais"
        constraints = [models.CheckConstraint(condition=models.Q(cidade='Sorocaba', estado='SP'), name='local_somente_sorocaba_sp')]

    def __str__(self):
        return self.nome

    def clean(self):
        super().clean()
        if self.cidade != 'Sorocaba' or self.estado != 'SP':
            raise ValidationError('O MVP atende somente Sorocaba/SP.')
        if (self.latitude is None) != (self.longitude is None):
            raise ValidationError('Informe latitude e longitude juntas.')


class FotoLocal(models.Model):
    local = models.ForeignKey(Local, on_delete=models.CASCADE, related_name='fotos')
    foto = models.ImageField(upload_to='locais/%Y/%m/')
    legenda = models.CharField(max_length=200, blank=True)


class Avaliacao(models.Model):
    local = models.ForeignKey(Local, on_delete=models.CASCADE, related_name='avaliacoes')
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    nota = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comentario = models.TextField(max_length=3000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-pk']
        constraints = [models.UniqueConstraint(fields=['local', 'autor'], name='avaliacao_unica_por_autor')]


class Perfil(models.Model):
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='perfil')
    nome = models.CharField(max_length=150, blank=True)
    preferencias = models.JSONField(default=list, blank=True, validators=[validar_preferencias])


class Favorito(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    local = models.ForeignKey(Local, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['usuario', 'local'], name='favorito_unico')]


TIPOS_PROBLEMA = [
    'rampa_ausente_ou_inadequada', 'calcada_em_mau_estado', 'elevador_indisponivel',
    'banheiro_nao_adaptado', 'vaga_acessivel_indisponivel',
    'piso_tatil_ausente_ou_danificado', 'obstaculo_na_via', 'outro',
]
STATUS = [('em_analise', 'Em análise'), ('confirmada', 'Confirmada'), ('resolvida', 'Resolvida')]


def gerar_protocolo():
    return 'AC-' + uuid4().hex.upper()


class Ocorrencia(models.Model):
    protocolo = models.CharField(max_length=35, unique=True, default=gerar_protocolo, editable=False)
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    endereco = models.CharField(max_length=500)
    latitude = models.DecimalField(max_digits=8, decimal_places=6, null=True, blank=True,
                                  validators=[MinValueValidator(-90), MaxValueValidator(90)])
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True,
                                   validators=[MinValueValidator(-180), MaxValueValidator(180)])
    tipo_problema = models.CharField(max_length=60, choices=[(x, x) for x in TIPOS_PROBLEMA])
    descricao = models.TextField(max_length=5000)
    foto = models.ImageField(upload_to='ocorrencias/%Y/%m/', blank=True)
    status = models.CharField(max_length=15, choices=STATUS, default='em_analise')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at', '-pk']


class HistoricoOcorrencia(models.Model):
    ocorrencia = models.ForeignKey(Ocorrencia, on_delete=models.CASCADE, related_name='historico')
    responsavel = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    status = models.CharField(max_length=15, choices=STATUS)
    justificativa = models.TextField(max_length=3000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'pk']
