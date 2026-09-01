from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Local(models.Model):
    nome = models.CharField(max_length=255)
    categoria = models.CharField(max_length=100)
    endereco = models.CharField(max_length=255)
    descricao = models.TextField(blank=True, default="")
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

    def __str__(self):
        return self.nome
