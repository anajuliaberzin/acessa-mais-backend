"""Avaliação conservadora, independente do formato e dos códigos do provider.

Os atributos atuais descrevem algumas barreiras, mas não atestam continuidade
de rampas, largura livre, travessias ou obstáculos. Não permitem recomendar
uma rota acessível nem calcular um score confiável, mesmo com extras completos.
"""


def identificar_barreiras(atributos):
    barreiras = []
    for atributo in atributos:
        tipo, valor = atributo["tipo"], atributo["valor"]
        if tipo == "tipo_via" and valor == "escada":
            tipo, descricao = "escada", "Escada identificada nos dados do trajeto."
        elif tipo == "superficie":
            descricao = f"Superfície {valor} informada no trajeto."
        elif tipo == "inclinacao":
            descricao = f"{valor}."
        else:
            continue
        barreiras.append({"tipo": tipo, "descricao": descricao, "trecho": atributo["trecho"]})
    return barreiras


def avaliar_rota(rota):
    return {
        "tempo_minutos": round(rota.duracao_segundos / 60, 2),
        "distancia_metros": rota.distancia_metros,
        "geometria": rota.geometria,
        "score_acessibilidade": None,
        "barreiras": identificar_barreiras(rota.atributos),
        "acessibilidade_avaliada": False,
        "nivel_confianca": "limitado",
    }


def comparar_rotas(rotas):
    # Comparar segundos originais, antes de arredondar. Distância desempata.
    ordenadas = sorted(rotas, key=lambda rota: (rota.duracao_segundos, rota.distancia_metros))
    avaliadas = [avaliar_rota(rota) for rota in ordenadas]
    return {
        "rota_rapida": avaliadas[0],
        "rota_acessivel": None,
        "alternativas": avaliadas[1:],
        "acessibilidade_avaliada": False,
        "nivel_confianca": "limitado",
        "mensagem": (
            "Não há dados suficientes para determinar uma rota mais acessível. "
            "A avaliação é parcial: as barreiras listadas são apenas as identificadas nos dados; "
            "uma lista vazia não significa ausência de barreiras."
        ),
    }
