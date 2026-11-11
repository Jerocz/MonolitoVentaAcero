"""Tareas en segundo plano (Celery + Redis como Message Broker).

- notificar_cotizacion_aprobada / notificar_cambio_etapa: correos al cliente.
- generar_reporte_ventas: reporte CSV pesado, fuera del ciclo de la peticion.
- crear_orden_pendiente: reintento con backoff si ms-fabricacion estaba caido.
- vencer_cotizaciones: tarea periodica (Celery Beat) que vence cotizaciones.
"""
import csv
import io
import logging

from celery import shared_task
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.mail import send_mail
from django.utils import timezone, translation
from django.utils.translation import gettext as _

from ventas.domain.excepciones import ServicioNoDisponibleError
from ventas.domain.reglas import id_desde_referencia
from ventas.infra.contenedor import Contenedor
from ventas.models import Cotizacion, Notificacion, ReporteVentas

log = logging.getLogger(__name__)


def _enviar(destinatario, asunto, cuerpo):
    send_mail(asunto, cuerpo, settings.DEFAULT_FROM_EMAIL, [destinatario], fail_silently=True)
    Notificacion.objects.create(destinatario=destinatario, asunto=asunto, cuerpo=cuerpo)


@shared_task
def notificar_cotizacion_aprobada(cotizacion_id, idioma=None):
    with translation.override(idioma or settings.LANGUAGE_CODE):
        cot = Cotizacion.objects.select_related("cliente").get(pk=cotizacion_id)
        asunto = _("Tu cotización %(ref)s fue aprobada") % {"ref": cot.referencia}
        cuerpo = _(
            "Hola %(cliente)s:\n\nRecibimos el anticipo de $%(anticipo)s para la cotización %(ref)s "
            "(total $%(total)s). Tu pedido ya entró a la fila de fabricación.\n\n%(empresa)s"
        ) % {"cliente": cot.cliente.nombre, "anticipo": f"{cot.anticipo:,.0f}", "ref": cot.referencia,
             "total": f"{cot.total:,.0f}", "empresa": settings.EMPRESA["NOMBRE"]}
        _enviar(cot.cliente.email, asunto, cuerpo)


@shared_task
def notificar_cambio_etapa(cotizacion_ref, estado_display, idioma=None):
    with translation.override(idioma or settings.LANGUAGE_CODE):
        cot = Cotizacion.objects.select_related("cliente").filter(pk=id_desde_referencia(cotizacion_ref)).first()
        if cot is None:
            return
        asunto = _("Tu pedido %(ref)s avanzó a: %(etapa)s") % {"ref": cotizacion_ref, "etapa": estado_display}
        cuerpo = _("Hola %(cliente)s:\n\nTu pedido %(ref)s ahora está en la etapa \"%(etapa)s\".\n\n%(empresa)s") % {
            "cliente": cot.cliente.nombre, "ref": cotizacion_ref, "etapa": estado_display,
            "empresa": settings.EMPRESA["NOMBRE"]}
        _enviar(cot.cliente.email, asunto, cuerpo)


@shared_task(bind=True, autoretry_for=(ServicioNoDisponibleError,), retry_backoff=5,
             retry_backoff_max=300, max_retries=8)
def crear_orden_pendiente(self, cotizacion_id):
    from ventas.services import CotizacionService
    CotizacionService().crear_orden_pendiente(cotizacion_id)


@shared_task
def generar_reporte_ventas(reporte_id, idioma=None):
    reporte = ReporteVentas.objects.get(pk=reporte_id)
    with translation.override(idioma or settings.LANGUAGE_CODE):
        try:
            cotizaciones = list(Cotizacion.objects.select_related("cliente").order_by("id"))
            try:
                estados = Contenedor.pagos().estado([c.referencia for c in cotizaciones])
            except ServicioNoDisponibleError:
                estados = {}
            salida = io.StringIO()
            escritor = csv.writer(salida)
            escritor.writerow([_("Referencia"), _("Fecha"), _("Cliente"), _("Tipo de cliente"), _("Estado"),
                               _("Total (COP)"), _("Anticipo (COP)"), _("Orden"), _("Saldo pagado")])
            for c in cotizaciones:
                estado_pago = estados.get(c.referencia)
                saldo = "" if estado_pago is None else (_("Sí") if estado_pago.saldo_pagado else _("No"))
                escritor.writerow([c.referencia, timezone.localtime(c.fecha_creacion).strftime("%Y-%m-%d %H:%M"),
                                   c.cliente.nombre, c.cliente.get_tipo_display(), c.get_estado_display(),
                                   f"{c.total:.2f}", f"{c.anticipo:.2f}", c.orden_ref or "", saldo])
            nombre = f"reporte_ventas_{reporte.pk}_{timezone.now():%Y%m%d_%H%M%S}.csv"
            reporte.archivo.save(nombre, ContentFile(salida.getvalue().encode("utf-8-sig")), save=False)
            reporte.filas = len(cotizaciones)
            reporte.estado = ReporteVentas.Estado.LISTO
            reporte.detalle = "" if estados or not cotizaciones else _("ms-pagos no respondió: columna de saldo vacía.")
        except Exception as e:  # el reporte queda marcado con error, no se pierde
            log.exception("Fallo el reporte %s", reporte_id)
            reporte.estado = ReporteVentas.Estado.ERROR
            reporte.detalle = str(e)[:255]
        reporte.terminado = timezone.now()
        reporte.save()


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
