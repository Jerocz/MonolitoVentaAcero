"""Cliente HTTP resiliente para hablar con microservicios y APIs externas.

  - Timeout: ninguna llamada espera indefinidamente.
  - Retry con backoff exponencial ante errores de red y 502/503/504
    (seguro porque los endpoints de escritura de los microservicios son idempotentes).
  - Circuit Breaker por servicio (ver circuit_breaker.py).
  - Propaga el idioma (Accept-Language) y un id de correlacion (X-Request-ID).
"""
import logging
import threading
import uuid

import requests
from django.conf import settings
from django.utils import translation
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ventas.domain.excepciones import ServicioNoDisponibleError
from ventas.infra.http.circuit_breaker import breaker_para

log = logging.getLogger(__name__)

_sesiones: dict[str, requests.Session] = {}
_lock_sesiones = threading.Lock()


def _sesion_para(nombre: str) -> requests.Session:
    with _lock_sesiones:
        if nombre not in _sesiones:
            reintentos = Retry(
                total=settings.RESILIENCIA["REINTENTOS"],
                backoff_factor=0.3,
                status_forcelist=(502, 503, 504),
                allowed_methods=None,  # todos: los POST de los microservicios son idempotentes
                raise_on_status=False,
            )
            sesion = requests.Session()
            sesion.mount("http://", HTTPAdapter(max_retries=reintentos, pool_maxsize=10))
            sesion.mount("https://", HTTPAdapter(max_retries=reintentos, pool_maxsize=10))
            _sesiones[nombre] = sesion
        return _sesiones[nombre]


class RespuestaHttp:
    def __init__(self, status: int, datos):
        self.status = status
        self.datos = datos

    @property
    def mensaje_error(self) -> str:
        if isinstance(self.datos, dict):
            return str(self.datos.get("error") or self.datos)
        return str(self.datos)


class ClienteHttp:
    """Envoltura de requests con timeout, reintentos, circuit breaker,
    propagacion del idioma (Accept-Language) y un id de correlacion."""

    def __init__(self, nombre: str, url_base: str, timeout: float | None = None):
        self.nombre = nombre
        self.url_base = url_base.rstrip("/")
        self.timeout = timeout or settings.RESILIENCIA["TIMEOUT_SEGUNDOS"]
        self.breaker = breaker_para(nombre)

    def get(self, ruta, **params) -> RespuestaHttp:
        return self._llamar("GET", ruta, params=params or None)

    def post(self, ruta, json=None) -> RespuestaHttp:
        return self._llamar("POST", ruta, json=json if json is not None else {})

    def _llamar(self, metodo, ruta, **kwargs) -> RespuestaHttp:
        if not self.breaker.permite_llamada():
            raise ServicioNoDisponibleError(self.nombre, "circuito abierto")
        cabeceras = {
            "Accept": "application/json",
            "Accept-Language": translation.get_language() or settings.LANGUAGE_CODE,
            "X-Request-ID": uuid.uuid4().hex,
        }
        url = f"{self.url_base}{ruta}"
        try:
            r = _sesion_para(self.nombre).request(metodo, url, headers=cabeceras, timeout=self.timeout, **kwargs)
        except requests.RequestException as e:
            self.breaker.registrar_fallo()
            log.warning("%s %s fallo: %s", metodo, url, e)
            raise ServicioNoDisponibleError(self.nombre, type(e).__name__) from e

        if r.status_code >= 500:
            self.breaker.registrar_fallo()
            raise ServicioNoDisponibleError(self.nombre, f"HTTP {r.status_code}")
        self.breaker.registrar_exito()
        try:
            datos = r.json()
        except ValueError:
            datos = r.text
        return RespuestaHttp(r.status_code, datos)
