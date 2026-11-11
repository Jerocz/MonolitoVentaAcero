"""Aplicacion Celery: procesos en segundo plano usando Redis como Message Broker.

Worker:  celery -A monolito_venta_acero worker -l info
Beat:    celery -A monolito_venta_acero beat -l info   (tareas periodicas)
"""
import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "monolito_venta_acero.settings.desarrollo")

app = Celery("monolito_venta_acero")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
