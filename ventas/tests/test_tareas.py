"""Tareas de Celery ejecutadas de forma sincrona (sin broker)."""
import tempfile
from datetime import date, timedelta

from django.core import mail
from django.test import override_settings

from ventas.models import Cliente, Cotizacion, Notificacion, ReporteVentas
from ventas.services import CotizacionService
from ventas.tasks import (
    generar_reporte_ventas,
    notificar_cambio_etapa,
    notificar_cotizacion_aprobada,
    vencer_cotizaciones,
)
from ventas.tests.dobles import ConDobles


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", MEDIA_ROOT=tempfile.mkdtemp())
class TareasTest(ConDobles):
    def setUp(self):
        super().setUp()
        self.cliente = Cliente.objects.create(nombre="Hotel", nit_o_cedula="1", email="h@test.co")
        self.cot = CotizacionService().crear_cotizacion(
            self.cliente.id, [{"producto_id": 1, "ancho_cm": 100, "largo_cm": 100}])

    def test_notificacion_de_cotizacion_en_el_idioma_del_usuario(self):
        notificar_cotizacion_aprobada(self.cot.id, "en")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("was approved", mail.outbox[0].subject)
        self.assertEqual(Notificacion.objects.get().destinatario, "h@test.co")

    def test_notificacion_cambio_etapa(self):
        notificar_cambio_etapa(self.cot.referencia, "Corte", "es")
        self.assertIn("Corte", mail.outbox[0].subject)

    def test_reporte_csv(self):
        reporte = ReporteVentas.objects.create()
        generar_reporte_ventas(reporte.id, "es")
        reporte.refresh_from_db()
        self.assertEqual(reporte.estado, ReporteVentas.Estado.LISTO)
        self.assertEqual(reporte.filas, 1)
        contenido = reporte.archivo.read().decode("utf-8-sig")
        self.assertIn("Referencia", contenido)
        self.assertIn(self.cot.referencia, contenido)

    def test_reporte_sin_pagos_disponible_igual_se_genera(self):
        self.pagos.caido = True
        reporte = ReporteVentas.objects.create()
        generar_reporte_ventas(reporte.id, "es")
        reporte.refresh_from_db()
        self.assertEqual(reporte.estado, ReporteVentas.Estado.LISTO)
        self.assertIn("ms-pagos", reporte.detalle)

    def test_vencer_cotizaciones(self):
        vieja = Cotizacion.objects.create(cliente=self.cliente, estado=Cotizacion.Estado.ENVIADA,
                                          fecha_vencimiento=date.today() - timedelta(days=1))
        self.assertEqual(vencer_cotizaciones(), 1)
        vieja.refresh_from_db()
        self.assertEqual(vieja.estado, Cotizacion.Estado.VENCIDA)
        self.cot.refresh_from_db()
        self.assertEqual(self.cot.estado, Cotizacion.Estado.APROBADA)  # las aprobadas no vencen
