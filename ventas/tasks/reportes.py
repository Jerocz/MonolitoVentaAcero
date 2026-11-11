"""Reporte de ventas en CSV, generado fuera del ciclo de la peticion web."""
import csv
import io
import logging

from celery import shared_task
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone, translation
from django.utils.translation import gettext as _

from ventas.domain.excepciones import ServicioNoDisponibleError
from ventas.infra.contenedor import Contenedor
from ventas.models import Cotizacion, ReporteVentas

log = logging.getLogger(__name__)


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
