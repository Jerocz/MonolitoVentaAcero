"""Reintentos de la saga cuando ms-fabricacion no estaba disponible."""
from celery import shared_task

from ventas.domain.excepciones import ServicioNoDisponibleError


@shared_task(bind=True, autoretry_for=(ServicioNoDisponibleError,), retry_backoff=5,
             retry_backoff_max=300, max_retries=8)
def crear_orden_pendiente(self, cotizacion_id):
    from ventas.services import CotizacionService
    CotizacionService().crear_orden_pendiente(cotizacion_id)
