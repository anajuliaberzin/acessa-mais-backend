from django.core.exceptions import ValidationError
from .acessibilidade import PESOS, ESTADOS


def validar_recursos(value):
    if not isinstance(value, dict) or set(value) - set(PESOS):
        raise ValidationError('Informe apenas os seis critérios de acessibilidade do MVP.')
    if any(estado not in ESTADOS for estado in value.values()):
        raise ValidationError('Estado de recurso inválido.')
