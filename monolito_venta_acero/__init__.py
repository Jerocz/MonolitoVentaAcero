# Carga la app de Celery al iniciar Django para que @shared_task la use.
from monolito_venta_acero.celery import app as celery_app

__all__ = ("celery_app",)
