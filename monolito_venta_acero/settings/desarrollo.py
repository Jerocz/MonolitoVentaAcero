"""Entorno local: python manage.py runserver / test."""
from monolito_venta_acero.settings.base import *  # noqa: F401,F403
from monolito_venta_acero.settings.entorno import env_lista, env_texto

DEBUG = True
SECRET_KEY = env_texto(
    "DJANGO_SECRET_KEY", "django-insecure-7g08jgp%=28^is&6r-#efx8b!)(31)m_+a$^afv4s8e%ag55_)")
ALLOWED_HOSTS = env_lista("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1],testserver")
