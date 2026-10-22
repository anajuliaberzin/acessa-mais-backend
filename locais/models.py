from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from .validators import validar_recursos


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
