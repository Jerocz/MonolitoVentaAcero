"""Saga de cotizacion y servicio de ordenes, con inyeccion de dependencias."""
from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError

from ventas.domain.excepciones import (
    PagoRechazadoError,
    PedidoInvalidoError,
    RecursoNoEncontradoError,
    ServicioNoDisponibleError,
)
from ventas.models import Cliente, Cotizacion, ItemCotizacion
from ventas.services import CotizacionService, OrdenService
from ventas.tests.dobles import ConDobles, FakeFabricacion, FakePagos

ITEM = [{"producto_id": 1, "ancho_cm": 100, "largo_cm": 100}]


class SagaCotizacionTest(ConDobles):
    def setUp(self):
        super().setUp()
        self.cliente = Cliente.objects.create(
            nombre="Test", nit_o_cedula="1", tipo=Cliente.Tipo.RESTAURANTE, email="t@test.co")

    def servicio(self, **kw):
        base = dict(catalogo=self.catalogo, pagos=self.pagos, fabricacion=self.fabricacion, cola=self.cola)
        return CotizacionService(**(base | kw))

    def test_cotizacion_aprobada_genera_orden_y_notifica(self):
        cot = self.servicio().crear_cotizacion(self.cliente.id, ITEM)
        cot.refresh_from_db()
        self.assertEqual(cot.estado, Cotizacion.Estado.APROBADA)
        self.assertEqual(cot.total, Decimal("100000.00"))
        self.assertEqual(cot.anticipo, Decimal("50000.00"))
        self.assertEqual(cot.orden_ref, 1)
        self.assertEqual(ItemCotizacion.objects.get(cotizacion=cot).producto_nombre, "Lamina")
        self.assertIn("cotizacion_aprobada", self.cola.nombres())

    def test_anticipo_rechazado_compensa_liberando_stock(self):
        with self.assertRaises(PagoRechazadoError):
            self.servicio(pagos=FakePagos(aprueba=False)).crear_cotizacion(self.cliente.id, ITEM)
        cot = Cotizacion.objects.get()
        self.assertEqual(cot.estado, Cotizacion.Estado.RECHAZADA)
        self.assertEqual(self.catalogo.liberadas, [cot.referencia])
        self.assertEqual(self.fabricacion.ordenes, {})

    def test_pagos_caido_compensa_y_avisa(self):
        with self.assertRaises(ServicioNoDisponibleError):
            self.servicio(pagos=FakePagos(caido=True)).crear_cotizacion(self.cliente.id, ITEM)
        self.assertEqual(Cotizacion.objects.get().estado, Cotizacion.Estado.RECHAZADA)
        self.assertEqual(len(self.catalogo.liberadas), 1)

    def test_regla_de_catalogo_no_deja_cotizacion(self):
        with self.assertRaises(PedidoInvalidoError):
            self.servicio().crear_cotizacion(self.cliente.id, [{"producto_id": 1, "ancho_cm": 30, "largo_cm": 100}])
        self.assertFalse(Cotizacion.objects.exists())

    def test_producto_inexistente(self):
        with self.assertRaises(RecursoNoEncontradoError):
            self.servicio().crear_cotizacion(self.cliente.id, [{"producto_id": 99, "ancho_cm": 100, "largo_cm": 100}])

    def test_sin_items(self):
        with self.assertRaises(PedidoInvalidoError):
            self.servicio().crear_cotizacion(self.cliente.id, [])

    def test_fabricacion_caida_no_pierde_la_venta(self):
        caida = FakeFabricacion(caido=True)
        cot = self.servicio(fabricacion=caida).crear_cotizacion(self.cliente.id, ITEM)
        self.assertEqual(cot.estado, Cotizacion.Estado.APROBADA)
        self.assertIsNone(cot.orden_ref)
        self.assertIn(("crear_orden", cot.id), self.cola.llamadas)
        # Cuando el servicio vuelve, la tarea de Celery crea la orden (idempotente).
        caida.caido = False
        self.servicio(fabricacion=caida).crear_orden_pendiente(cot.id)
        cot.refresh_from_db()
        self.assertEqual(cot.orden_ref, 1)
        self.assertIsNone(self.servicio(fabricacion=caida).crear_orden_pendiente(cot.id))


class OrdenServiceTest(ConDobles):
    def setUp(self):
        super().setUp()
        cliente = Cliente.objects.create(nombre="Hotel", nit_o_cedula="2", tipo=Cliente.Tipo.HOTEL, email="h@test.co")
        self.cot = CotizacionService().crear_cotizacion(cliente.id, ITEM)

    def test_avanzar_etapa_notifica(self):
        orden = OrdenService().avanzar_etapa(self.cot.orden_ref)
        self.assertEqual(orden.estado, "CORTE")
        self.assertIn("cambio_etapa", self.cola.nombres())

    def test_pagar_saldo(self):
        OrdenService().pagar_saldo(self.cot.orden_ref)
        filas, pagos_ok = OrdenService().listar_con_pagos()
        self.assertTrue(pagos_ok)
        self.assertTrue(filas[0]["saldo_pagado"])

    def test_listar_degrada_si_pagos_esta_caido(self):
        filas, pagos_ok = OrdenService(pagos=FakePagos(caido=True)).listar_con_pagos()
        self.assertFalse(pagos_ok)
        self.assertEqual(len(filas), 1)


class ValidacionModeloTest(ConDobles):
    """El modelo se autovalida en save() (full_clean()) - correccion de la Entrega 1."""

    def test_cliente_con_email_invalido_no_se_guarda(self):
        with self.assertRaises(DjangoValidationError):
            Cliente.objects.create(nombre="X", nit_o_cedula="1", email="no-es-correo")

    def test_cotizacion_con_total_negativo_no_se_guarda(self):
        cliente = Cliente.objects.create(nombre="X", nit_o_cedula="1", email="x@test.co")
        with self.assertRaises(DjangoValidationError):
            Cotizacion.objects.create(cliente=cliente, fecha_vencimiento="2026-12-01", total=-1)

    def test_item_con_subtotal_cero_no_se_guarda(self):
        cliente = Cliente.objects.create(nombre="X", nit_o_cedula="1", email="x@test.co")
        cot = Cotizacion.objects.create(cliente=cliente, fecha_vencimiento="2026-12-01")
        with self.assertRaises(DjangoValidationError):
            ItemCotizacion.objects.create(cotizacion=cot, producto_ref=1, producto_nombre="L", producto_tipo="LAMINA",
                                          ancho_cm=100, largo_cm=100, cantidad=1, subtotal=0)
