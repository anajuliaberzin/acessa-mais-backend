# ACESSA+

Backend inicial do projeto **ACESSA+**, preparado com:

- Python
- Django
- Django REST Framework
- PostgreSQL
- `psycopg`
- `django-cors-headers`
- `python-dotenv`

Esta etapa cria apenas a base técnica do backend. Ainda não existem models de domínio, serializers, views, endpoints de negócio, autenticação ou regras de negócio.

## Objetivo desta base

Deixar o projeto pronto para as próximas etapas de desenvolvimento, com:

- estrutura padrão do Django;
- configurações centralizadas;
- conexão com PostgreSQL via variáveis de ambiente;
- suporte a CORS para o frontend Angular;
- painel administrativo inicial do Django.

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

## Pré-requisitos

Instale e tenha disponíveis:

- Python 3.14 ou compatível;
- PostgreSQL 18 ou compatível;
- PowerShell no Windows.

O serviço do PostgreSQL precisa estar em execução. No Windows, é possível verificar com:

```powershell
Get-Service postgresql*
```

## Criar o banco de dados

O servidor PostgreSQL e o banco `acessa_mais` são coisas diferentes. Se o banco ainda não existir, abra o PostgreSQL pelo terminal:

```powershell
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -d postgres
```

Informe a senha do usuário `postgres` e execute:

```sql
CREATE DATABASE acessa_mais;
\q
```

Se o comando `psql` já estiver configurado no `PATH`, também é possível executar:

```powershell
psql -U postgres -d postgres
```

## Configurar as variáveis de ambiente

Crie o `.env` somente se ele ainda não existir:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Depois preencha o arquivo `.env` com os valores locais:

```env
DJANGO_SECRET_KEY=uma-chave-secreta-forte
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:4200

DB_NAME=acessa_mais
DB_USER=postgres
DB_PASSWORD=sua-senha-real-do-postgres
DB_HOST=localhost
DB_PORT=5432
```

O arquivo `.env` contém credenciais e não deve ser commitado. Ele já está protegido pelo `.gitignore`.

## Instalar e executar o projeto

No PowerShell, dentro da pasta do projeto:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python manage.py check
python manage.py migrate
```

Se o comando `py` não estiver disponível, use o Python instalado localmente:

```powershell
& "C:\Users\regis\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m venv .venv
```

## Criar o administrador

Para acessar o painel administrativo do Django:

```powershell
python manage.py createsuperuser
```

Informe o usuário, e-mail e senha solicitados.

## Iniciar o servidor

```powershell
python manage.py runserver
```

Acesse:

```text
http://127.0.0.1:8000/admin/
```

Nesta etapa, o projeto ainda não possui endpoints de API de domínio. O endereço disponível é o painel administrativo inicial do Django.

## Observações

- O banco informado em `DB_NAME` precisa existir antes de executar `migrate`.
- A senha em `DB_PASSWORD` deve ser a senha real do usuário configurado no PostgreSQL.
- Não execute novamente `Copy-Item .env.example .env` se o `.env` já estiver preenchido.
- O frontend Angular poderá usar a origem configurada em `CORS_ALLOWED_ORIGINS` quando os endpoints forem implementados.
