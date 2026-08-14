"""Pruebas: servicios (con inyeccion de dependencias), estrategias de precio
y la API DRF con sus codigos de estado."""
from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from ventas.domain.excepciones import PagoRechazadoError, PedidoInvalidoError
from ventas.domain.precios import estrategia_para
from ventas.infra.pasarelas import PasarelaPago, ResultadoPago
from ventas.models import Cliente, Cotizacion, Freidora, Lamina, Meson
from ventas.services import CotizacionService


class PasarelaAprueba(PasarelaPago):
    def cobrar(self, monto, email_cliente):
        return ResultadoPago(True, "TEST-OK")


class PasarelaRechaza(PasarelaPago):
    def cobrar(self, monto, email_cliente):
        return ResultadoPago(False, "TEST-FAIL")


class ServicioYEstrategiaTest(APITestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(
            nombre="Test", nit_o_cedula="1", tipo=Cliente.Tipo.RESTAURANTE, email="t@test.co")
        self.lamina = Lamina.objects.create(nombre="Lamina", calibre_acero=304, precio_base_m2=100000, stock_m2=100)
        self.meson = Meson.objects.create(nombre="Meson", calibre_acero=304, precio_base_m2=100000, stock_m2=100)
        self.freidora = Freidora.objects.create(nombre="Freidora", calibre_acero=304, precio_base_m2=2000000, stock_m2=99)

    def test_cotizacion_aprobada_genera_orden(self):
        cot = CotizacionService(pasarela=PasarelaAprueba()).crear_cotizacion(
            self.cliente.id, [{"producto_id": self.lamina.id, "ancho_cm": 100, "largo_cm": 100}])
        self.assertEqual(cot.estado, Cotizacion.Estado.APROBADA)
        self.assertTrue(hasattr(cot, "orden"))

    def test_strategy_meson_cuesta_15_por_ciento_mas(self):
        precio_lamina = estrategia_para("LAMINA").calcular(Decimal("100000"), 100, 100, 1)
        precio_meson = estrategia_para("MESON").calcular(Decimal("100000"), 100, 100, 1)
        self.assertEqual(precio_meson, (precio_lamina * Decimal("1.15")).quantize(Decimal("0.01")))

    def test_freidora_no_es_a_medida(self):
        self.assertFalse(estrategia_para("FREIDORA").es_a_medida)

    def test_anticipo_rechazado_revierte(self):
        with self.assertRaises(PagoRechazadoError):
            CotizacionService(pasarela=PasarelaRechaza()).crear_cotizacion(
                self.cliente.id, [{"producto_id": self.lamina.id, "ancho_cm": 100, "largo_cm": 100}])
        self.assertEqual(Cotizacion.objects.filter(estado=Cotizacion.Estado.APROBADA).count(), 0)


class ApiTest(APITestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(
            nombre="Test", nit_o_cedula="1", tipo=Cliente.Tipo.HOTEL, email="t@test.co")
        self.lamina = Lamina.objects.create(nombre="Lamina", calibre_acero=304, precio_base_m2=100000, stock_m2=100)

    def test_crear_cotizacion_devuelve_201(self):
        r = self.client.post(reverse("api_crear_cotizacion"), {
            "cliente_id": self.cliente.id,
            "items": [{"producto_id": self.lamina.id, "ancho_cm": 100, "largo_cm": 100, "cantidad": 1}],
        }, format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r.data["estado"], "APROBADA")

    def test_body_invalido_devuelve_400(self):
        r = self.client.post(reverse("api_crear_cotizacion"), {"items": []}, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cliente_inexistente_devuelve_404(self):
        r = self.client.post(reverse("api_crear_cotizacion"), {
            "cliente_id": 9999,
            "items": [{"producto_id": self.lamina.id, "ancho_cm": 100, "largo_cm": 100}],
        }, format="json")
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    def test_ancho_invalido_devuelve_409(self):
        r = self.client.post(reverse("api_crear_cotizacion"), {
            "cliente_id": self.cliente.id,
            "items": [{"producto_id": self.lamina.id, "ancho_cm": 30, "largo_cm": 100}],
        }, format="json")
        self.assertEqual(r.status_code, status.HTTP_409_CONFLICT)
