"""Consumo de API de TERCEROS mediante el Patron Adapter.

Proveedor: ExchangeRate-API (endpoint abierto https://open.er-api.com/v6/latest/COP).
Su respuesta tiene un formato propio:

    {"result": "success", "base_code": "COP", "time_last_update_unix": 1762732951,
     "rates": {"COP": 1, "USD": 0.000257, "EUR": 0.000221, ...}}

`ExchangeRateApiAdapter` traduce ese formato al DTO del dominio
(`TasaCambioDTO`) e implementa el puerto `TasaCambioPort`. El resto del
sistema (vistas, servicios, plantillas) nunca conoce al proveedor: si manana
se cambia por el Banco de la Republica u otro, solo se escribe otro adaptador.
"""
import logging
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from django.core.cache import cache

from ventas.domain.dtos import TasaCambioDTO
from ventas.domain.excepciones import ServicioNoDisponibleError
from ventas.domain.puertos import TasaCambioPort
from ventas.infra.http import ClienteHttp

log = logging.getLogger(__name__)


class ExchangeRateApiAdapter(TasaCambioPort):
    """Adapter (adaptee = API de ExchangeRate-API, target = TasaCambioPort)."""
    NOMBRE = "exchangerate-api"
    SEGUNDOS_CACHE = 60 * 60  # el proveedor actualiza una vez al dia

    def __init__(self, url_base: str, cliente_http: ClienteHttp | None = None):
        self.http = cliente_http or ClienteHttp(self.NOMBRE, url_base)

    def obtener(self, origen="COP", destino="USD"):
        clave = f"tasa:{origen}:{destino}"
        en_cache = cache.get(clave)
        if en_cache:
            return en_cache
        r = self.http.get(f"/v6/latest/{origen}")
        tasa = self._adaptar(r.datos, origen, destino) if r.status == 200 else None
        if tasa is None:
            raise ServicioNoDisponibleError(self.NOMBRE, f"respuesta no valida (HTTP {r.status})")
        cache.set(clave, tasa, self.SEGUNDOS_CACHE)
        return tasa

    def _adaptar(self, datos, origen, destino) -> TasaCambioDTO | None:
        """Traduce el formato del proveedor al formato del dominio."""
        if not isinstance(datos, dict) or datos.get("result") != "success":
            return None
        try:
            valor = Decimal(str(datos["rates"][destino]))
        except (KeyError, InvalidOperation, TypeError):
            return None
        marca = datos.get("time_last_update_unix")
        return TasaCambioDTO(
            origen=datos.get("base_code", origen), destino=destino, valor=valor,
            fuente="ExchangeRate-API",
            actualizada=datetime.fromtimestamp(marca, tz=timezone.utc) if marca else None)


class TasaCambioFija(TasaCambioPort):
    """Respaldo local configurable (cuando el proveedor externo no responde)."""

    def __init__(self, valor_cop_usd: Decimal):
        self.valor = Decimal(valor_cop_usd)

    def obtener(self, origen="COP", destino="USD"):
        return TasaCambioDTO(origen=origen, destino=destino, valor=self.valor,
                             fuente="respaldo", es_respaldo=True)


class TasaCambioConRespaldo(TasaCambioPort):
    """Fallback: intenta el proveedor principal y, si falla, usa el respaldo.
    Asi la pagina nunca se cae porque una API externa no responda."""

    def __init__(self, principal: TasaCambioPort, respaldo: TasaCambioPort):
        self.principal = principal
        self.respaldo = respaldo

    def obtener(self, origen="COP", destino="USD"):
        try:
            return self.principal.obtener(origen, destino)
        except ServicioNoDisponibleError as e:
            log.info("Tasa de cambio: usando respaldo (%s)", e)
            return self.respaldo.obtener(origen, destino)
