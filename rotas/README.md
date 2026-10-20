# API de comparação de rotas

`POST /api/rotas/comparar/` é público, aceita somente coordenadas numéricas em JSON e não usa banco, JWT ou geocodificação. O escopo de produto é Sorocaba/SP; esta API valida os limites globais de latitude/longitude, mas não implementa validação de fronteira municipal ou descoberta de municípios.

## Configuração

No `.env` do backend (não versionar credenciais):

```dotenv
ROUTING_API_KEY=<chave do OpenRouteService>
ROUTING_TIMEOUT_SECONDS=10
```

Chave obtida no painel do [OpenRouteService](https://openrouteservice.org/). Timeout em segundos, maior que zero e até 60. A configuração ausente/inválida retorna 503, sem impedir a inicialização das demais APIs. Não há novas dependências Python.

O adaptador usa HTTPS em `https://api.openrouteservice.org/v2/directions/foot-walking/geojson`, solicita até três trajetos com `alternative_routes`, preferência `fastest`, unidade em metros, sem instruções de navegação e com `extra_info` de `waytype`, `surface` e `steepness`. O número efetivo de alternativas depende do provider. A chamada usa timeout de operações de rede, limite de resposta de 5 MiB e não segue redirecionamentos. Não há retries automáticos.

## Request

```http
POST /api/rotas/comparar/
Content-Type: application/json

{
  "origem": {"latitude": -23.5015, "longitude": -47.4526},
  "destino": {"latitude": -23.5100, "longitude": -47.4600}
}
```

Origem/destino e ambas as coordenadas são obrigatórios. Latitude entre -90 e 90; longitude entre -180 e 180. Texto, booleanos, estruturas inválidas e números não finitos são rejeitados. Endereços não são convertidos para coordenadas. Pontos iguais são enviados ao provider, que poderá retornar um trajeto de distância zero ou ausência de rota.

## Response 200

Exemplo **de fixture de teste**, não um resultado medido em Sorocaba:

```json
{
  "rota_rapida": {
    "tempo_minutos": 12.0,
    "distancia_metros": 950.0,
    "geometria": {
      "type": "LineString",
      "coordinates": [[-47.4526, -23.5015], [-47.46, -23.51]]
    },
    "score_acessibilidade": null,
    "barreiras": [],
    "acessibilidade_avaliada": false,
    "nivel_confianca": "limitado"
  },
  "rota_acessivel": null,
  "alternativas": [],
  "acessibilidade_avaliada": false,
  "nivel_confianca": "limitado",
  "mensagem": "Não há dados suficientes para determinar uma rota mais acessível. A avaliação é parcial: as barreiras listadas são apenas as identificadas nos dados; uma lista vazia não significa ausência de barreiras."
}
```

- GeoJSON usa **[longitude, latitude]**, em WGS84. Não inverter a ordem para renderizar no mapa. Eventual elevação é descartada na normalização 2D.
- A rota mais rápida é a de menor `duration` em segundos entre as retornadas, antes de arredondar para minutos. Distância é critério de desempate. Isso não garante o ótimo entre todos os caminhos da cidade.
- `alternativas` contém as demais opções retornadas pelo provider, ordenadas pelos mesmos critérios. Usa o mesmo contrato da rota rápida e não recebe rótulo de acessibilidade.
- `barreiras` contém apenas indícios nos atributos realmente recebidos. Cada item tem `tipo`, `descricao` e `trecho: [indice_inicial, indice_final]`, referenciando os pontos da geometria. Não são coordenadas calculadas pela aplicação. Inclinação é descritiva, não uma classificação legal de segurança.
- Códigos de extras desconhecidos, incompletos ou malformados não são inferidos como acessíveis e são ignorados. Geometria e resumo obrigatórios inválidos retornam 502.

## Limitação de acessibilidade

O perfil de caminhada disponibiliza tipos de via (incluindo escadas), superfície e classes de inclinação quando presentes no grafo. Esses dados não comprovam continuidade de rampas, largura útil, condições das travessias, obstáculos temporários ou adequação a uma necessidade individual. Não usamos a mera ausência de escadas ou uma distância maior como prova de acessibilidade.

**Nesta versão, `rota_acessivel` e `score_acessibilidade` são sempre `null`, e `acessibilidade_avaliada` é `false`.** A avaliação de barreiras é parcial, mesmo quando os três extras existem. Não há regra fictícia de pontuação ou duplicação da rota rápida. Para recomendar uma candidata, será necessário obter cobertura suficiente de atributos e definir/validar critérios de acessibilidade. A regra isolada em `accessibility_service.py` permite essa evolução sem mudar o transporte HTTP.

As descrições atuais identificam escadas (waytype 8), determinadas superfícies explicitamente informadas (não pavimentada, cascalho, terra, solo, gelo/neve, areia, grama) e classes de subida/descida informadas. Não presumem calçada irregular, rampa ausente ou travessia inadequada sem evidência.

Fontes oficiais consultadas:

- [Extras e disponibilidade por perfil](https://giscience.github.io/openrouteservice/api-reference/endpoints/directions/extra-info/)
- [Tipos de via](https://giscience.github.io/openrouteservice/api-reference/endpoints/directions/extra-info/waytype)
- [Superfícies](https://giscience.github.io/openrouteservice/api-reference/endpoints/directions/extra-info/surface)
- [Inclinações](https://giscience.github.io/openrouteservice/api-reference/endpoints/directions/extra-info/steepness)

## Erros

Validação DRF retorna 400 com os erros por campo. Erros de serviço retornam `{"codigo": "...", "detail": "mensagem pública"}`:

| HTTP | Situação |
| --- | --- |
| 400 | Campos/coordenadas/JSON inválidos |
| 404 | Coleção de rotas vazia ou ORS 2009/2010 (rota/ponto sem caminho) |
| 502 | Resposta inválida, redirecionamento ou rejeição inesperada do provider |
| 503 | Chave/configuração ausente, rede indisponível, credencial recusada, quota excedida ou falha externa |
| 504 | Timeout de rede ou HTTP 408/504 do provider |

Mensagens externas e credenciais não são repassadas ao cliente. Um 404 genérico do provider não é confundido com ausência de trajeto.

## Testes e execução

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test rotas --verbosity 2
.\.venv\Scripts\python.exe manage.py runserver
```

Os testes fazem POST pela stack DRF e mockam exclusivamente o transporte do provider: não precisam de chave real, rede, migrations ou PostgreSQL. Incluem contrato da chamada, normalização, seleção, erros, limites, casos sem alternativas e insuficiência de acessibilidade.

O frontend em `/rotas` envia as coordenadas para esta API e desenha a geometria GeoJSON em SVG, sem mapa base. Trata `rota_acessivel: null` e não converte score nulo em zero. Abra-o em `http://localhost:4200/rotas`, com o Django em `http://127.0.0.1:8000`; a origem do frontend deve constar em `CORS_ALLOWED_ORIGINS`.

Em 20/10/2026, uma verificação explícita do componente Angular com transporte HTTP real (sem mock) passou: formulário → Django → OpenRouteService → opções e troca do traçado. A consulta das coordenadas acima retornou 18,45 minutos, 1.537,7 metros e duas alternativas. O preflight CORS também retornou 200 com a origem permitida. Essa consulta não confirma acessibilidade, e os resultados podem variar. A inspeção visual em navegador desktop/mobile continua pendente. Os testes regulares permanecem isolados da rede e não consomem quota do provider.
