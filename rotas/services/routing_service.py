"""Adaptador OpenRouteService. Nenhum formato específico do ORS sai desta camada."""
import json
import math
from dataclasses import dataclass
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from django.conf import settings


ORS_URL = "https://api.openrouteservice.org/v2/directions/foot-walking/geojson"
MAX_RESPONSE_BYTES = 5 * 1024 * 1024


class RoutingError(Exception):
    def __init__(self, codigo, mensagem, status):
        super().__init__(mensagem)
        self.codigo = codigo
        self.mensagem = mensagem
        self.status = status


def sem_rota():
    return RoutingError("rota_nao_encontrada", "Nenhuma rota encontrada entre os pontos informados.", 404)


def resposta_invalida():
    return RoutingError("resposta_invalida", "O serviço de rotas retornou uma resposta inválida.", 502)


class SemRedirecionamento(HTTPRedirectHandler):
    # Não encaminhar a chave para um destino de redirecionamento.
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


@dataclass(frozen=True)
class Rota:
    duracao_segundos: float
    distancia_metros: float
    geometria: dict
    # Atributos semânticos normalizados por trecho, não códigos do provider.
    atributos: tuple


def numero(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


# Códigos publicados em /api-reference/endpoints/directions/extra-info/.
# Ausência de atributo ou código desconhecido nunca significa ausência de barreira.
SUPERFICIES = {
    2: "não pavimentada", 8: "cascalho compactado", 10: "cascalho",
    11: "terra", 12: "solo", 13: "gelo/neve", 15: "areia", 17: "grama",
}
INCLINACOES = {1: "1% a menos de 4%", 2: "4% a menos de 7%", 3: "7% a menos de 10%",
              4: "10% a menos de 16%", 5: "16% ou mais"}


def normalizar_atributos(extras, total_pontos):
    atributos = []
    if not isinstance(extras, dict):
        return ()
    for nome in ("waytype", "surface", "steepness"):
        extra = extras.get(nome)
        if not isinstance(extra, dict) or not isinstance(extra.get("values"), list):
            continue
        for trecho in extra["values"]:
            if (not isinstance(trecho, list) or len(trecho) != 3
                    or any(type(x) is not int for x in trecho)):
                continue
            inicio, fim, valor = trecho
            if not 0 <= inicio < fim < total_pontos:
                continue
            atributo = None
            if nome == "waytype" and valor == 8:
                atributo = {"tipo": "tipo_via", "valor": "escada"}
            elif nome == "surface" and valor in SUPERFICIES:
                atributo = {"tipo": "superficie", "valor": SUPERFICIES[valor]}
            elif nome == "steepness" and abs(valor) in INCLINACOES:
                sentido = "Subida" if valor > 0 else "Descida"
                atributo = {"tipo": "inclinacao", "valor": f"{sentido} de {INCLINACOES[abs(valor)]}"}
            if atributo:
                atributos.append({**atributo, "trecho": [inicio, fim]})
    return tuple(atributos)


def normalizar_resposta(payload):
    if not isinstance(payload, dict) or payload.get("type") != "FeatureCollection":
        raise resposta_invalida()
    features = payload.get("features")
    if not isinstance(features, list):
        raise resposta_invalida()
    if not features:
        raise sem_rota()
    rotas = []
    for feature in features:
        if not isinstance(feature, dict) or feature.get("type") != "Feature":
            raise resposta_invalida()
        propriedades, geometria = feature.get("properties"), feature.get("geometry")
        if not isinstance(propriedades, dict) or not isinstance(geometria, dict):
            raise resposta_invalida()
        resumo, pontos = propriedades.get("summary"), geometria.get("coordinates")
        if (not isinstance(resumo, dict) or geometria.get("type") != "LineString"
                or not isinstance(pontos, list) or len(pontos) < 2):
            raise resposta_invalida()
        duracao, distancia = resumo.get("duration"), resumo.get("distance")
        if not all(numero(x) and x >= 0 for x in (duracao, distancia)):
            raise resposta_invalida()
        for ponto in pontos:
            if (not isinstance(ponto, list) or len(ponto) not in (2, 3)
                    or not all(numero(x) for x in ponto)
                    or not -180 <= ponto[0] <= 180 or not -90 <= ponto[1] <= 90):
                raise resposta_invalida()
        rotas.append(Rota(
            duracao, distancia,
            {"type": "LineString", "coordinates": [ponto[:2] for ponto in pontos]},
            normalizar_atributos(propriedades.get("extras"), len(pontos)),
        ))
    return rotas


def buscar_rotas(origem, destino):
    chave = settings.ROUTING_API_KEY.strip()
    try:
        timeout = float(settings.ROUTING_TIMEOUT_SECONDS)
        if not math.isfinite(timeout) or not 0 < timeout <= 60:
            raise ValueError
    except (TypeError, ValueError):
        raise RoutingError("configuracao_indisponivel", "O serviço de rotas não está configurado corretamente.", 503) from None
    if not chave:
        raise RoutingError("configuracao_indisponivel", "O serviço de rotas ainda não está configurado.", 503)
    body = {
        "coordinates": [[p["longitude"], p["latitude"]] for p in (origem, destino)],
        "preference": "fastest", "units": "m", "instructions": False,
        "alternative_routes": {"target_count": 3, "share_factor": 0.6, "weight_factor": 1.4},
        "extra_info": ["waytype", "surface", "steepness"],
    }
    request = Request(ORS_URL, data=json.dumps(body).encode("utf-8"), method="POST", headers={
        "Authorization": chave, "Content-Type": "application/json", "Accept": "application/geo+json",
    })
    try:
        with build_opener(SemRedirecionamento()).open(request, timeout=timeout) as response:
            data = response.read(MAX_RESPONSE_BYTES + 1)
            if len(data) > MAX_RESPONSE_BYTES:
                raise resposta_invalida()
            payload = json.loads(data)
    except HTTPError as exc:
        try:
            error = json.loads(exc.read(MAX_RESPONSE_BYTES)).get("error", {})
            codigo = error.get("code") if isinstance(error, dict) else None
        except (ValueError, AttributeError, OSError, HTTPException):
            codigo = None
        finally:
            exc.close()
        if exc.code in (400, 404) and codigo in (2009, 2010):
            raise sem_rota() from None
        if exc.code in (408, 504):
            raise RoutingError("tempo_esgotado", "O serviço de rotas demorou a responder. Tente novamente.", 504) from None
        status = 503 if exc.code in (401, 403, 429) or exc.code >= 500 else 502
        raise RoutingError("provider_indisponivel", "O serviço de rotas está indisponível. Tente novamente mais tarde.", status) from None
    except (TimeoutError, URLError) as exc:
        if isinstance(exc, TimeoutError) or isinstance(getattr(exc, "reason", None), TimeoutError):
            raise RoutingError("tempo_esgotado", "O serviço de rotas demorou a responder. Tente novamente.", 504) from None
        raise RoutingError("provider_indisponivel", "O serviço de rotas está indisponível. Tente novamente mais tarde.", 503) from None
    except (ValueError, HTTPException):
        raise resposta_invalida() from None
    except OSError:
        raise RoutingError("provider_indisponivel", "O serviço de rotas está indisponível. Tente novamente mais tarde.", 503) from None
    return normalizar_resposta(payload)
