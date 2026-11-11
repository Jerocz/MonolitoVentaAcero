"""API REST del monolito (DRF) y sus codigos de estado."""
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from ventas.models import Cliente
from ventas.tests.dobles import ConDobles


class ApiTest(ConDobles, APITestCase):
    def setUp(self):
        super().setUp()
        self.cliente = Cliente.objects.create(nombre="Test", nit_o_cedula="1", tipo=Cliente.Tipo.HOTEL, email="t@test.co")

    def _crear(self, **item):
        cuerpo = {"cliente_id": self.cliente.id,
                  "items": [{"producto_id": 1, "ancho_cm": 100, "largo_cm": 100, "cantidad": 1} | item]}
        return self.client.post(reverse("api_crear_cotizacion"), cuerpo, format="json")

    def test_crear_cotizacion_devuelve_201(self):
        r = self._crear()
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r.data["estado"], "APROBADA")
        self.assertEqual(r.data["referencia"], f"COT-{r.data['id']}")

    def test_body_invalido_devuelve_400(self):
        r = self.client.post(reverse("api_crear_cotizacion"), {"items": []}, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cliente_inexistente_devuelve_404(self):
        r = self.client.post(reverse("api_crear_cotizacion"), {
            "cliente_id": 9999, "items": [{"producto_id": 1, "ancho_cm": 100, "largo_cm": 100}]}, format="json")
        self.assertEqual(r.status_code, status.HTTP_404_NOT_FOUND)

    def test_ancho_invalido_devuelve_409(self):
        self.assertEqual(self._crear(ancho_cm=30).status_code, status.HTTP_409_CONFLICT)

    def test_microservicio_caido_devuelve_503(self):
        self.catalogo.caido = True
        self.assertEqual(self._crear().status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    def test_productos_vienen_del_microservicio(self):
        r = self.client.get(reverse("api_productos"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data[0]["precio_base_m2"], "100000")

    def test_avanzar_y_saldo(self):
        orden_id = self._crear().data["orden_ref"]
        self.assertEqual(self.client.post(reverse("api_avanzar", args=[orden_id])).data["estado"], "CORTE")
        self.assertEqual(self.client.post(reverse("api_saldo", args=[orden_id])).status_code, 200)
        self.assertEqual(self.client.post(reverse("api_avanzar", args=[99])).status_code, 404)

    def test_tasa_de_cambio_via_adapter(self):
        r = self.client.get(reverse("api_tasa_cambio"))
        self.assertEqual(r.data["destino"], "USD")
        self.assertEqual(r.data["valor"], "0.00025")

    def test_servicio_aliado(self):
        r = self.client.get(reverse("api_aliado"))
        self.assertTrue(r.data["disponible"])
