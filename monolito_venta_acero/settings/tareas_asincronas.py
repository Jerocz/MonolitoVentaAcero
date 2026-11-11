"""Celery (Redis como Message Broker), cache y envio de correos."""
from monolito_venta_acero.settings.entorno import env_bool, env_texto

REDIS_URL = env_texto("REDIS_URL")
if REDIS_URL:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.redis.RedisCache",
                          "LOCATION": REDIS_URL, "KEY_PREFIX": "monolito"}}
else:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

CELERY_BROKER_URL = env_texto("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = env_texto("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
CELERY_TASK_ALWAYS_EAGER = env_bool("CELERY_TASK_ALWAYS_EAGER", False)
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_BROKER_TRANSPORT_OPTIONS = {"max_retries": 1, "interval_start": 0, "interval_step": 0.2}
# Si el broker esta caido, .delay() falla rapido en vez de bloquear la peticion web.
CELERY_TASK_PUBLISH_RETRY_POLICY = {"max_retries": 1, "interval_start": 0, "interval_step": 0.2, "interval_max": 0.5}
CELERY_TIMEZONE = "America/Bogota"
CELERY_BEAT_SCHEDULE = {
    "vencer-cotizaciones-cada-hora": {
        "task": "ventas.tasks.mantenimiento.vencer_cotizaciones",
        "schedule": 60 * 60,
    },
}

EMAIL_BACKEND = env_texto("DJANGO_EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = env_texto("DJANGO_DEFAULT_FROM_EMAIL", "ventas@integralestorresb.co")
