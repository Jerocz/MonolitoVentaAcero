"""
Pruebas unitarias del flujo de cotizacion.

Demuestran Inyeccion de Dependencias (se inyecta una pasarela falsa),
el polimorfismo de productos y las reglas del Builder.
"""
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from ventas.domain.excepciones import PagoRechazadoError, PedidoInvalidoError
from ventas.infra.pasarelas import PasarelaPago, ResultadoPago
from ventas.models import Cliente, Cotizacion, Freidora, Lamina, Meson
from ventas.services import CotizacionService


class PasarelaAprueba(PasarelaPago):
    def cobrar(self, monto, email_cliente):
        return ResultadoPago(aprobado=True, referencia="TEST-OK")


class PasarelaRechaza(PasarelaPago):
    def cobrar(self, monto, email_cliente):
        return ResultadoPago(aprobado=False, referencia="TEST-FAIL")


class CotizacionServiceTest(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(
            nombre="Test", nit_o_cedula="1", tipo=Cliente.Tipo.RESTAURANTE, email="t@test.co"
        )
        self.lamina = Lamina.objects.create(
            nombre="Lamina", calibre_acero=304, precio_base_m2=100000, stock_m2=100
        )
        self.meson = Meson.objects.create(
            nombre="Meson", calibre_acero=304, precio_base_m2=100000, stock_m2=100
        )
        self.freidora = Freidora.objects.create(
            nombre="Freidora", calibre_acero=304, precio_base_m2=2000000, stock_m2=99
        )

    def test_cotizacion_aprobada_genera_orden_y_anticipo(self):
        servicio = CotizacionService(pasarela=PasarelaAprueba())  # DI
        cot = servicio.crear_cotizacion(
            self.cliente.id,
            [{"producto_id": self.lamina.id, "ancho_cm": 100, "largo_cm": 100}],
        )
        self.assertEqual(cot.estado, Cotizacion.Estado.APROBADA)
        self.assertEqual(cot.total, Decimal("100000.00"))
        self.assertTrue(hasattr(cot, "orden"))
        self.assertEqual(cot.orden.pagos.count(), 1)  # solo el anticipo

    def test_meson_cuesta_15_por_ciento_mas_que_lamina(self):
        """Polimorfismo: mismo tamano, precios distintos por subclase."""
        precio_lamina = self.lamina.calcular_precio(100, 100, 1)
        precio_meson = self.meson.calcular_precio(100, 100, 1)
        self.assertEqual(precio_meson, (precio_lamina * Decimal("1.15")).quantize(Decimal("0.01")))

    def test_ancho_invalido_en_producto_a_medida_falla(self):
        servicio = CotizacionService(pasarela=PasarelaAprueba())
        with self.assertRaises(PedidoInvalidoError):
            servicio.crear_cotizacion(
                self.cliente.id,
                [{"producto_id": self.lamina.id, "ancho_cm": 30, "largo_cm": 100}],
            )

    def test_freidora_no_exige_ancho_minimo(self):
        """La Freidora NO es a la medida: un ancho pequeno no debe fallar."""
        servicio = CotizacionService(pasarela=PasarelaAprueba())
        cot = servicio.crear_cotizacion(
            self.cliente.id,
            [{"producto_id": self.freidora.id, "ancho_cm": 10, "largo_cm": 10, "cantidad": 1}],
        )
        self.assertEqual(cot.estado, Cotizacion.Estado.APROBADA)

    def test_anticipo_rechazado_revierte_todo(self):
        servicio = CotizacionService(pasarela=PasarelaRechaza())
        with self.assertRaises(PagoRechazadoError):
            servicio.crear_cotizacion(
                self.cliente.id,
                [{"producto_id": self.lamina.id, "ancho_cm": 100, "largo_cm": 100}],
            )
        # No debe quedar ninguna cotizacion APROBADA ni ninguna orden.
        self.assertEqual(Cotizacion.objects.filter(estado=Cotizacion.Estado.APROBADA).count(), 0)

    def test_la_pagina_carga(self):
        resp = self.client.get(reverse("cotizacion_form"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Cotizacion de acero")
