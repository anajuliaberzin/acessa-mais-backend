"""Busca de endereços no ORS/Pelias, restrita a Sorocaba/SP."""
import hashlib
import json
from http.client import HTTPException
from urllib.parse import urlencode
from urllib.request import Request, build_opener
from urllib.error import HTTPError, URLError

from django.conf import settings
from django.core.cache import cache
from .routing_service import RoutingError, SemRedirecionamento, numero


def buscar_enderecos(texto):
    chave = settings.ROUTING_API_KEY.strip()
    if not chave:
        raise RoutingError('configuracao_indisponivel', 'A busca de endereços ainda não está configurada.', 503)
    cache_key = 'enderecos:ors:v1:' + hashlib.sha256(texto.casefold().encode()).hexdigest()
    salvo = cache.get(cache_key)
    if salvo is not None:
        return salvo
    params = {'text': f'{texto}, Sorocaba, São Paulo, Brasil', 'boundary.country': 'BRA',
              'focus.point.lat': -23.5015, 'focus.point.lon': -47.4526,
              'layers': 'address,street,venue', 'size': 10}
    request = Request('https://api.heigit.org/pelias/v1/search?' + urlencode(params),
                      headers={'Authorization': chave, 'Accept': 'application/json'})
    try:
        with build_opener(SemRedirecionamento()).open(request, timeout=10) as response:
            data = response.read(1024 * 1024 + 1)
            if len(data) > 1024 * 1024:
                raise ValueError('resposta excessiva')
            payload = json.loads(data)
        if not isinstance(payload, dict) or not isinstance(payload.get('features'), list):
            raise ValueError('formato inválido')
        resultados = []
        for feature in payload['features']:
            if not isinstance(feature, dict):
                raise ValueError('feature inválida')
            p = feature.get('properties', {})
            g = feature.get('geometry', {})
            if not isinstance(p, dict) or not isinstance(g, dict):
                raise ValueError('endereço inválido')
            # Não confundir a região administrativa de Sorocaba com o município.
            if str(p.get('locality', '')).casefold() != 'sorocaba':
                continue
            if p.get('country_a') not in ('BRA', 'BR') or not (p.get('region_a') == 'SP' or p.get('region') == 'São Paulo'):
                continue
            xy = g.get('coordinates')
            if (g.get('type') != 'Point' or not isinstance(xy, list) or len(xy) != 2
                    or not all(numero(n) for n in xy) or not -180 <= xy[0] <= 180 or not -90 <= xy[1] <= 90
                    or not isinstance(p.get('label'), str)):
                raise ValueError('coordenadas inválidas')
            resultados.append({'endereco': p['label'], 'latitude': xy[1], 'longitude': xy[0],
                               'aproximado': p.get('layer') == 'street'})
    except HTTPError as exc:
        status = 429 if exc.code == 429 else 503
        exc.close()
        raise RoutingError('busca_indisponivel', 'A busca de endereços está indisponível. Tente novamente em instantes.', status) from None
    except (TimeoutError, URLError, OSError, HTTPException):
        raise RoutingError('busca_indisponivel', 'Não foi possível consultar os endereços. Tente novamente.', 503) from None
    except (ValueError, TypeError, OverflowError):
        raise RoutingError('resposta_invalida', 'A busca de endereços retornou uma resposta inválida.', 502) from None
    cache.set(cache_key, resultados, 86400)
    return resultados
