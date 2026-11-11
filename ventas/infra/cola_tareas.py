"""Adaptador del puerto ColaTareasPort sobre Celery + Redis.

Si el broker no esta disponible, el error se registra pero NO tumba la
peticion del usuario (la venta ya quedo hecha; la notificacion es secundaria).
"""
import logging

from django.utils import translation

from ventas.domain.puertos import ColaTareasPort

log = logging.getLogger(__name__)


class ColaTareasCelery(ColaTareasPort):
    def _encolar(self, tarea, *args):
        try:
            tarea.delay(*args)
        except Exception as e:  # broker caido: degradacion controlada
            log.error("No se pudo encolar %s: %s", tarea.name, e)

    def notificar_cotizacion_aprobada(self, cotizacion_id):
        from ventas.tasks import notificar_cotizacion_aprobada
        self._encolar(notificar_cotizacion_aprobada, cotizacion_id, translation.get_language())

    def notificar_cambio_etapa(self, cotizacion_ref, estado_display):
        from ventas.tasks import notificar_cambio_etapa
        self._encolar(notificar_cambio_etapa, cotizacion_ref, estado_display, translation.get_language())

    def programar_creacion_orden(self, cotizacion_id):
        from ventas.tasks import crear_orden_pendiente
        self._encolar(crear_orden_pendiente, cotizacion_id)

    def generar_reporte(self, reporte_id):
        from ventas.tasks import generar_reporte_ventas
        self._encolar(generar_reporte_ventas, reporte_id, translation.get_language())
