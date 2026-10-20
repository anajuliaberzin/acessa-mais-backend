from django.core.exceptions import ValidationError
from .acessibilidade import PESOS, ESTADOS


def validar_recursos(value):
    if not isinstance(value, dict) or set(value) - set(PESOS):
        raise ValidationError('Informe apenas os seis critérios de acessibilidade do MVP.')
    if any(estado not in ESTADOS for estado in value.values()):
        raise ValidationError('Estado de recurso inválido.')


PREFERENCIAS = ('cadeirante', 'deficiencia_visual', 'deficiencia_auditiva', 'mobilidade_reduzida')


def validar_preferencias(value):
    if not isinstance(value, list) or any(item not in PREFERENCIAS for item in value):
        raise ValidationError('Preferências inválidas.')
    if len(value) != len(set(value)):
        raise ValidationError('Preferências repetidas.')
