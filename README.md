# ACESSA+

Backend inicial do projeto **ACESSA+**, preparado com:

- Python
- Django
- Django REST Framework
- PostgreSQL
- `psycopg`
- `django-cors-headers`
- `python-dotenv`

Esta etapa cria apenas a base técnica do backend. Ainda não existem models de domínio, serializers, views, endpoints, autenticação ou regras de negócio.

## Objetivo desta base

Deixar o projeto pronto para as próximas etapas de desenvolvimento, com:

- estrutura padrão do Django;
- configurações centralizadas;
- conexão com PostgreSQL via variáveis de ambiente;
- suporte a CORS para o frontend Angular;
- URL base inicial da aplicação.

## Estrutura inicial

```text
acessa-mais-backend/
  manage.py
  requirements.txt
  .env
  .env.example
  .gitignore
  README.md
  config/
    __init__.py
    asgi.py
    settings.py
    urls.py
    wsgi.py
```

## Arquivos de configuração

- `config/settings.py`: configurações base do Django, DRF, PostgreSQL, CORS e variáveis de ambiente.
- `config/urls.py`: URLs raiz do projeto.
- `.env.example`: modelo de variáveis necessárias para rodar localmente.
- `requirements.txt`: dependências Python do backend.

## Variáveis de ambiente

Crie o arquivo `.env` a partir de `.env.example` e preencha:

```env
DJANGO_SECRET_KEY=uma-chave-secreta-forte
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:4200

DB_NAME=acessa_mais
DB_USER=postgres
DB_PASSWORD=sua-senha
DB_HOST=localhost
DB_PORT=5432
```

## Primeiros comandos para rodar

No PowerShell, usando o Python instalado no Windows:

```powershell
& "C:\Users\regis\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
python manage.py migrate
python manage.py runserver
```

## Observações

- O PostgreSQL precisa estar instalado e rodando.
- O banco informado em `DB_NAME` precisa existir.
- O frontend Angular poderá consumir a API via HTTP/JSON em `http://localhost:4200`.

