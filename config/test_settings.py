"""Testes isolados: não usam nem alteram o PostgreSQL local."""
from .settings import *

SECRET_KEY = 'somente-testes-isolados-chave-nao-utilizada-em-producao'

DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
MEDIA_ROOT = BASE_DIR / '.test-media'
