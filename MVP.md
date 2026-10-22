# ACESSA+ — regras e contratos do MVP

## Regras oficiais

- Abrangência única: Sorocaba/SP. Sem seletor de cidade, multi-tenancy ou ranking entre municípios.
- Consultas de locais, busca, filtros, detalhes e mapa são públicas.
- Conteúdo do usuário exige JWT (Django REST Framework + Simple JWT).
- Reportes têm autor obtido do JWT, protocolo único e histórico de atendimento.
- Nota de acessibilidade é objetiva; avaliações de usuários são independentes e não alteram a nota.
- Não implementar nesta etapa: pesos personalizados, reputação, gamificação, validação automática de denúncias ou machine learning.
- Essas decisões não devem ser alteradas sem consultar o responsável pelo projeto.

## Nota de acessibilidade

A única implementação da regra fica em `locais/acessibilidade.py`.

| Critério | Peso |
| --- | ---: |
| Rampa **ou** acesso sem degrau (`rampa`) | 20 |
| Banheiro adaptado | 20 |
| Vaga acessível | 15 |
| Elevador | 15 |
| Piso tátil | 15 |
| Recurso auditivo | 15 |

Cada critério assume `atendido`, `nao_atendido`, `nao_aplicavel` ou `nao_informado`.
Somente os dois primeiros entram no denominador; apenas `atendido` soma pontos obtidos.
Nota = pontos obtidos / pontos aplicáveis × 100.

Classificação pelo valor exato: abaixo de 40 baixa; de 40 até menos de 70 parcial;
de 70 até menos de 90 boa; a partir de 90 alta acessibilidade.

Tratamento aprovado: cadastro incompleto ou sem critérios aplicáveis recebe `nota: null` e
`classificacao: null`, exibidos como “Nota não calculada”, sem participar dos destaques ou da média.
A apresentação usa uma casa decimal; arredondamento visual não altera a classificação.

## Cadastro e publicação

Locais são administrados pelo Django admin. O formulário contém os seis critérios com aplicabilidade.
Cidade/estado ficam limitados a Sorocaba/SP. `localizacao_confirmada` exige revisão do endereço
pela pessoa responsável pelo cadastro; somente locais confirmados são publicados.

**Locais anteriores à migration ficam preservados, mas não publicados até essa revisão.**
Não é atribuída nota fictícia aos cadastros existentes. Categorias novas são normalizadas para
minúsculas pelo admin. A confirmação administrativa e a declaração do autor da ocorrência não
constituem validação geográfica automática.

## API

Todas as URLs abaixo têm prefixo `/api`. Listagens paginadas usam
`{count, next, previous, results}`; `page` começa em 1; `page_size` padrão 20 e máximo 100.

### Consulta pública

- `GET /locais/`: filtros `nome`, `categoria`, `necessidade`, `recursos`, `bbox`, `ordenacao`.
- `GET /locais/{id}/`: recursos, nota/classificação, fotos e média/quantidade de avaliações subjetivas.
- `GET /locais/filtros/`: categorias cadastradas, recursos e necessidades disponíveis.
- `GET /locais/mapa/`: locais com ambas as coordenadas; filtros iguais aos de consulta.
- `GET /locais/{id}/avaliacoes/`: avaliações paginadas.

`recursos` aceita nomes separados por vírgula e exige todos os recursos solicitados.
`necessidade` aceita `mobilidade`, `visual`, `auditiva`, retornando locais com ao menos um recurso
atendido do grupo. Não representa certificação de adequação a todas as necessidades da pessoa.
`bbox` usa `oeste,sul,leste,norte`; `ordenacao` aceita `nome` ou `acessibilidade`.
Ordenação por acessibilidade exclui notas não calculadas; empates usam nome e ID.

### Usuário autenticado

- `POST /locais/{id}/avaliacoes/`: `nota` de 1 a 5 e `comentario`. Uma avaliação por usuário/local.
- `GET/POST /ocorrencias/`: listar as próprias ocorrências ou criar reporte.
- `GET /ocorrencias/{id}/`: detalhe e histórico da própria ocorrência.
- `GET /ocorrencias/{id}/foto/`: foto privada, acessível ao autor e aos gestores.

Criação de ocorrência aceita JSON ou multipart com `endereco`, `tipoProblema`, `descricao`,
`confirmadoSorocaba: true`, coordenadas opcionais (ambas, até seis casas decimais) e `foto` opcional.
Imagem JPEG, PNG ou WebP válida de até 5 MB. Autor, protocolo e status inicial são definidos pelo servidor.
O front utiliza `REQUIRE_AUTH` na requisição para ativar o interceptor JWT existente.

## Execução e verificação

```powershell
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe manage.py migrate
.venv/Scripts/python.exe manage.py check
.venv/Scripts/python.exe manage.py test --settings=config.test_settings
```

Os testes usam SQLite temporário e não alteram o PostgreSQL configurado no `.env`.
Para acessar a plataforma, utilizar usuários Django existentes ou criados no admin.

Fotos de locais são públicas. Em desenvolvimento apenas `/media/locais/` é servido diretamente;
fotos de ocorrências passam pelo endpoint autenticado. Em hospedagem, não expor a pasta inteira
`media/ocorrencias/` publicamente. Uploads não são versionados.


## Branch delivery

Authenticated reports, private photos and tracking.
