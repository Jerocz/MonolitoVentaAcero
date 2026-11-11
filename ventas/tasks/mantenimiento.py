"""Tareas periodicas (Celery Beat)."""
import logging

from celery import shared_task
from django.utils import timezone

from ventas.models import Cotizacion

log = logging.getLogger(__name__)


@shared_task
def vencer_cotizaciones():
    """Marca como VENCIDA toda cotizacion no aprobada cuya vigencia ya paso."""
    hoy = timezone.localdate()
    vencidas = Cotizacion.objects.filter(
        fecha_vencimiento__lt=hoy,
        estado__in=[Cotizacion.Estado.BORRADOR, Cotizacion.Estado.ENVIADA],
    ).update(estado=Cotizacion.Estado.VENCIDA)
    log.info("Cotizaciones vencidas: %s", vencidas)
    return vencidas
