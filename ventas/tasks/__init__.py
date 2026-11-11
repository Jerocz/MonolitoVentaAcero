"""Tareas en segundo plano (Celery + Redis como Message Broker).

    notificaciones.py  correos al cliente (cotizacion aprobada, cambio de etapa)
    reportes.py        reporte de ventas CSV
    ordenes.py         reintento con backoff si ms-fabricacion estaba caido
    mantenimiento.py   tarea periodica que vence cotizaciones (Celery Beat)

Celery descubre este paquete con autodiscover_tasks() (busca `ventas.tasks`).
"""
from ventas.tasks.mantenimiento import vencer_cotizaciones
from ventas.tasks.notificaciones import notificar_cambio_etapa, notificar_cotizacion_aprobada
from ventas.tasks.ordenes import crear_orden_pendiente
from ventas.tasks.reportes import generar_reporte_ventas

__all__ = ["crear_orden_pendiente", "generar_reporte_ventas", "notificar_cambio_etapa",
           "notificar_cotizacion_aprobada", "vencer_cotizaciones"]
