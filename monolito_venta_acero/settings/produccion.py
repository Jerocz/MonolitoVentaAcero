"""Entorno de despliegue (Docker Compose en AWS EC2)."""
from monolito_venta_acero.settings.base import *  # noqa: F401,F403
from monolito_venta_acero.settings.entorno import env_lista, env_obligatoria

DEBUG = False
SECRET_KEY = env_obligatoria("DJANGO_SECRET_KEY")
ALLOWED_HOSTS = env_lista("DJANGO_ALLOWED_HOSTS", "*")

SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False  # el formulario lo lee del HTML, no de JavaScript
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
