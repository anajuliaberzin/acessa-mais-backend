"""Regra única de acessibilidade do MVP Sorocaba. Sem influência de avaliações."""
PESOS = {
    'rampa': 20, 'banheiro_adaptado': 20, 'vaga_acessivel': 15,
    'elevador': 15, 'piso_tatil': 15, 'recurso_auditivo': 15,
}
ESTADOS = ('atendido', 'nao_atendido', 'nao_aplicavel', 'nao_informado')
NECESSIDADES = {
    'mobilidade': ('rampa', 'banheiro_adaptado', 'vaga_acessivel', 'elevador'),
    'visual': ('piso_tatil',),
    'auditiva': ('recurso_auditivo',),
}


def calcular_acessibilidade(recursos):
    obtidos = sum(peso for nome, peso in PESOS.items() if recursos.get(nome) == 'atendido')
    aplicaveis = sum(peso for nome, peso in PESOS.items()
                     if recursos.get(nome) in ('atendido', 'nao_atendido'))
    completo = all(recursos.get(nome) in ESTADOS[:3] for nome in PESOS)
    resultado = {'pontos_obtidos': obtidos, 'pontos_aplicaveis': aplicaveis,
                 'nota': None, 'classificacao': None, 'cadastro_completo': completo}
    # Sem denominador ou informações completas não existe resultado matemático confiável.
    if not completo or not aplicaveis:
        return resultado
    nota = obtidos / aplicaveis * 100
    classificacao = ('alta acessibilidade' if nota >= 90 else 'boa acessibilidade' if nota >= 70
                     else 'acessibilidade parcial' if nota >= 40 else 'baixa acessibilidade')
    return {**resultado, 'nota': nota, 'classificacao': classificacao}
