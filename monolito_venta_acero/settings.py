"""
Configuracion de Django para el monolito (Entrega 2: ecosistema hibrido).

Todo lo que cambia entre entornos (local, Docker, AWS EC2) se lee de
variables de entorno (12-factor). Los valores por defecto permiten correr
el proyecto localmente sin Docker.
"""
import os
from pathlib import Path

import dj_database_url
from django.utils.translation import gettext_lazy as _

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(nombre: str, defecto: bool = False) -> bool:
    return os.getenv(nombre, str(defecto)).strip().lower() in ("1", "true", "si", "yes", "on")


def env_lista(nombre: str, defecto: str = "") -> list[str]:
    return [v.strip() for v in os.getenv(nombre, defecto).split(",") if v.strip()]


SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "django-insecure-7g08jgp%=28^is&6r-#efx8b!)(31)m_+a$^afv4s8e%ag55_)")  # solo desarrollo
DEBUG = env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = env_lista("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1]")
CSRF_TRUSTED_ORIGINS = env_lista("DJANGO_CSRF_TRUSTED_ORIGINS")

# Detras del API Gateway (Nginx): confiar en las cabeceras que el reenvia.
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'rest_framework',
    'ventas',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',  # i18n: elige el idioma por sesion/cookie/navegador
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'monolito_venta_acero.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.template.context_processors.i18n',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'ventas.context_processors.empresa',
            ],
        },
    },
]

WSGI_APPLICATION = 'monolito_venta_acero.wsgi.application'


# Base de datos: PostgreSQL en Docker (DATABASE_URL); SQLite en local.
DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}", conn_max_age=60, conn_health_checks=True),
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# ---------------------------------------------------------------- i18n
LANGUAGE_CODE = "es"
LANGUAGES = [
    ("es", _("Español")),
    ("en", _("Inglés")),
]
LOCALE_PATHS = [BASE_DIR / "locale"]
TIME_ZONE = 'America/Bogota'
USE_I18N = True
USE_TZ = True


# ---------------------------------------------------------------- estaticos y media
STATIC_URL = '/static/'
STATIC_ROOT = Path(os.getenv("DJANGO_STATIC_ROOT", BASE_DIR / "staticfiles"))
MEDIA_URL = '/media/'
MEDIA_ROOT = Path(os.getenv("DJANGO_MEDIA_ROOT", BASE_DIR / "media"))


# ---------------------------------------------------------------- cache
REDIS_URL = os.getenv("REDIS_URL", "")
if REDIS_URL:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.redis.RedisCache",
                          "LOCATION": REDIS_URL, "KEY_PREFIX": "monolito"}}
else:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}


# ---------------------------------------------------------------- Celery (Message Broker)
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
CELERY_TASK_ALWAYS_EAGER = env_bool("CELERY_TASK_ALWAYS_EAGER", False)
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_BROKER_TRANSPORT_OPTIONS = {"max_retries": 1, "interval_start": 0, "interval_step": 0.2}
# Si el broker esta caido, .delay() falla rapido en vez de bloquear la peticion web.
CELERY_TASK_PUBLISH_RETRY_POLICY = {"max_retries": 1, "interval_start": 0, "interval_step": 0.2, "interval_max": 0.5}
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULE = {
    "vencer-cotizaciones-cada-hora": {
        "task": "ventas.tasks.vencer_cotizaciones",
        "schedule": 60 * 60,
    },
}

EMAIL_BACKEND = os.getenv("DJANGO_EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = os.getenv("DJANGO_DEFAULT_FROM_EMAIL", "ventas@integralestorresb.co")


# ---------------------------------------------------------------- microservicios
MICROSERVICIOS = {
    "CATALOGO": os.getenv("MS_CATALOGO_URL", "http://localhost:5001"),
    "PAGOS": os.getenv("MS_PAGOS_URL", "http://localhost:5002"),
    "FABRICACION": os.getenv("MS_FABRICACION_URL", "http://localhost:5003"),
}
RESILIENCIA = {
    "TIMEOUT_SEGUNDOS": float(os.getenv("HTTP_TIMEOUT_SEGUNDOS", "4")),
    "REINTENTOS": int(os.getenv("HTTP_REINTENTOS", "2")),
    "UMBRAL_FALLOS": int(os.getenv("CIRCUITO_UMBRAL_FALLOS", "3")),
    "SEGUNDOS_CIRCUITO_ABIERTO": int(os.getenv("CIRCUITO_SEGUNDOS_ABIERTO", "20")),
}

# API de terceros (Adapter) y servicio del equipo aliado.
TASA_CAMBIO_API_URL = os.getenv("TASA_CAMBIO_API_URL", "https://open.er-api.com")
TASA_COP_USD_RESPALDO = os.getenv("TASA_COP_USD_RESPALDO", "0.00025")
ALIADO_NOMBRE = os.getenv("ALIADO_NOMBRE", "Equipo aliado")
ALIADO_API_URL = os.getenv("ALIADO_API_URL", "")

EMPRESA = {
    "NOMBRE": "Integrales Torres B.",
    "TELEFONO": "+57 300 000 0000",
    "TELEFONO_TEL": "+573000000000",
    "CORREO": "ventas@integralestorresb.co",
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"consola": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["consola"], "level": os.getenv("DJANGO_LOG_LEVEL", "INFO")},
}
