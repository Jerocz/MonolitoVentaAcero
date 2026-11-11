"""Circuit breaker, cliente HTTP, Adapter de terceros y Adapter del aliado."""
from decimal import Decimal

from django.core.cache import cache
from django.test import SimpleTestCase, override_settings

from ventas.domain.excepciones import ServicioNoDisponibleError
from ventas.infra.aliado import AliadoHttpAdapter, normalizar
from ventas.infra.http import CircuitBreaker, ClienteHttp, RespuestaHttp
from ventas.infra.terceros import ExchangeRateApiAdapter, TasaCambioConRespaldo, TasaCambioFija


class Reloj:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


class CircuitBreakerTest(SimpleTestCase):
    def test_abre_tras_umbral_y_pasa_a_semi_abierto(self):
        reloj = Reloj()
        cb = CircuitBreaker("x", umbral_fallos=2, segundos_abierto=10, reloj=reloj)
        cb.registrar_fallo()
        self.assertTrue(cb.permite_llamada())
        cb.registrar_fallo()
        self.assertEqual(cb.estado, CircuitBreaker.ABIERTO)
        self.assertFalse(cb.permite_llamada())
        reloj.t = 11
        self.assertEqual(cb.estado, CircuitBreaker.SEMI_ABIERTO)
        cb.registrar_exito()
        self.assertEqual(cb.estado, CircuitBreaker.CERRADO)


@override_settings(RESILIENCIA={"TIMEOUT_SEGUNDOS": 0.5, "REINTENTOS": 0,
                                "UMBRAL_FALLOS": 2, "SEGUNDOS_CIRCUITO_ABIERTO": 60})
class ClienteHttpTest(SimpleTestCase):
    def test_servicio_inalcanzable_lanza_error_de_dominio_y_abre_circuito(self):
        cliente = ClienteHttp("prueba-inalcanzable", "http://127.0.0.1:9")
        for _ in range(2):
            with self.assertRaises(ServicioNoDisponibleError):
                cliente.get("/x")
        with self.assertRaises(ServicioNoDisponibleError) as ctx:
            cliente.get("/x")
        self.assertIn("circuito abierto", str(ctx.exception))


class HttpFalso:
    def __init__(self, status, datos):
        self.respuesta = RespuestaHttp(status, datos)
        self.llamadas = 0

    def get(self, ruta, **params):
        self.llamadas += 1
        return self.respuesta


class AdapterTercerosTest(SimpleTestCase):
    RESPUESTA_PROVEEDOR = {"result": "success", "base_code": "COP", "time_last_update_unix": 1762732951,
                           "rates": {"COP": 1, "USD": 0.000257, "EUR": 0.000221}}

    def setUp(self):
        cache.clear()

    def test_adapta_el_formato_del_proveedor_al_dominio(self):
        http = HttpFalso(200, self.RESPUESTA_PROVEEDOR)
        tasa = ExchangeRateApiAdapter("http://x", cliente_http=http).obtener("COP", "USD")
        self.assertEqual(tasa.valor, Decimal("0.000257"))
        self.assertEqual(tasa.convertir(Decimal("100000")), Decimal("25.70"))
        self.assertIsNotNone(tasa.actualizada)
        ExchangeRateApiAdapter("http://x", cliente_http=http).obtener("COP", "USD")
        self.assertEqual(http.llamadas, 1)  # segunda vez sale de la cache

    def test_respuesta_no_valida_lanza_error(self):
        with self.assertRaises(ServicioNoDisponibleError):
            ExchangeRateApiAdapter("http://x", cliente_http=HttpFalso(200, {"result": "error"})).obtener()

    def test_fallback_a_tasa_de_respaldo(self):
        principal = ExchangeRateApiAdapter("http://x", cliente_http=HttpFalso(500, {}))
        tasa = TasaCambioConRespaldo(principal, TasaCambioFija(Decimal("0.0003"))).obtener()
        self.assertTrue(tasa.es_respaldo)
        self.assertEqual(tasa.valor, Decimal("0.0003"))


class AdapterAliadoTest(SimpleTestCase):
    def test_normaliza_distintos_formatos(self):
        self.assertEqual(normalizar([{"a": 1, "b": {"x": 1}}]), [{"a": 1}])
        self.assertEqual(normalizar({"total": 1, "items": [{"n": "x"}]}), [{"n": "x"}])
        self.assertEqual(normalizar({"nombre": "solo"}), [{"nombre": "solo"}])
        self.assertEqual(normalizar("texto"), [])

    def test_sin_url_configurada_no_falla(self):
        info = AliadoHttpAdapter("Aliado", "").consultar()
        self.assertFalse(info.disponible)
        self.assertIn("ALIADO_API_URL", info.mensaje)
