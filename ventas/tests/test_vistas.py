"""Vistas HTML: formularios robustos, PRG, mensajes y degradacion controlada."""
import tempfile

from django.test import override_settings
from django.urls import reverse

from ventas.models import Cliente, Cotizacion, ReporteVentas
from ventas.tests.dobles import ConDobles


class VistasTest(ConDobles):
    def setUp(self):
        super().setUp()
        self.cliente = Cliente.objects.create(nombre="Camila", nit_o_cedula="1", email="c@test.co")

    def _post(self, **datos):
        base = {"cliente_id": self.cliente.id, "producto_id": 1, "ancho_cm": "70", "largo_cm": "150", "cantidad": "1"}
        return self.client.post(reverse("cotizacion_form"), base | datos)

    def test_inicio_muestra_catalogo_y_precio_en_usd(self):
        r = self.client.get(reverse("cotizacion_form"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Freidora")
        self.assertContains(r, "US$25")  # 100.000 COP * 0,00025

    def test_cotizar_redirige_post_redirect_get(self):
        r = self._post()
        cot = Cotizacion.objects.get()
        self.assertRedirects(r, f"{reverse('cotizacion_form')}?cotizacion={cot.id}#cotizador",
                             fetch_redirect_response=False)
        pagina = self.client.get(r["Location"])
        self.assertContains(pagina, cot.referencia)

    def test_campos_invalidos_muestran_error_por_campo(self):
        r = self._post(ancho_cm="abc", cantidad="0")
        self.assertContains(r, 'aria-invalid="true"', count=2, status_code=400)
        self.assertContains(r, "El ancho debe ser un número", status_code=400)
        self.assertFalse(Cotizacion.objects.exists())

    def test_ancho_minimo_se_valida_en_el_formulario(self):
        r = self._post(ancho_cm="30")
        self.assertContains(r, "el ancho mínimo es 60 cm", status_code=400)

    def test_cliente_obligatorio(self):
        r = self._post(cliente_id="")
        self.assertContains(r, "Elige el cliente", status_code=400)

    def test_catalogo_caido_no_tumba_la_pagina(self):
        self.catalogo.caido = True
        r = self.client.get(reverse("cotizacion_form"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "no está disponible en este momento")

    def test_fabricacion_caida_no_tumba_la_pagina(self):
        self.fabricacion.caido = True
        self.assertEqual(self.client.get(reverse("cotizacion_form")).status_code, 200)

    def test_acciones_de_orden_con_mensajes(self):
        self._post()
        orden_id = Cotizacion.objects.get().orden_ref
        r = self.client.post(reverse("avanzar_etapa", args=[orden_id]), follow=True)
        self.assertContains(r, "pasó a la etapa")
        r = self.client.post(reverse("pagar_saldo", args=[orden_id]), follow=True)
        self.assertContains(r, "Saldo de la orden")
        r = self.client.post(reverse("avanzar_etapa", args=[999]), follow=True)
        self.assertContains(r, "La orden no existe")

    def test_integraciones(self):
        r = self.client.get(reverse("integraciones"))
        self.assertContains(r, "/api/catalogo/publico/v1/productos")
        self.assertContains(r, "Envios")
        self.assertContains(r, "0,000250")

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_solicitar_reporte_lo_encola(self):
        r = self.client.post(reverse("procesos"), follow=True)
        reporte = ReporteVentas.objects.get()
        self.assertIn(("reporte", reporte.id), self.cola.llamadas)
        self.assertContains(r, "en cola")

    def test_salud_viva(self):
        self.assertEqual(self.client.get(reverse("salud_viva")).json()["estado"], "ok")
