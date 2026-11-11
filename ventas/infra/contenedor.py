"""Contenedor de dependencias (composition root).

Es el UNICO lugar que sabe que implementacion concreta va detras de cada
puerto. Las vistas y servicios piden `Contenedor.catalogo()` etc. y reciben
una abstraccion. Las pruebas reemplazan las implementaciones con
`Contenedor.sobrescribir(catalogo=FakeCatalogo(), ...)`.
"""
from decimal import Decimal

from django.conf import settings

from ventas.domain.puertos import (
    CatalogoPort,
    ColaTareasPort,
    FabricacionPort,
    PagosPort,
    ServicioAliadoPort,
    TasaCambioPort,
)


class Contenedor:
    _sobrescritos: dict = {}

    @classmethod
    def sobrescribir(cls, **implementaciones):
        cls._sobrescritos.update(implementaciones)

    @classmethod
    def restablecer(cls):
        cls._sobrescritos.clear()

    @classmethod
    def _o(cls, nombre, fabrica):
        return cls._sobrescritos.get(nombre) or fabrica()

    @classmethod
    def catalogo(cls) -> CatalogoPort:
        from ventas.infra.microservicios import CatalogoHttpAdapter
        return cls._o("catalogo", lambda: CatalogoHttpAdapter(settings.MICROSERVICIOS["CATALOGO"]))

    @classmethod
    def pagos(cls) -> PagosPort:
        from ventas.infra.microservicios import PagosHttpAdapter
        return cls._o("pagos", lambda: PagosHttpAdapter(settings.MICROSERVICIOS["PAGOS"]))

    @classmethod
    def fabricacion(cls) -> FabricacionPort:
        from ventas.infra.microservicios import FabricacionHttpAdapter
        return cls._o("fabricacion", lambda: FabricacionHttpAdapter(settings.MICROSERVICIOS["FABRICACION"]))

    @classmethod
    def tasa_cambio(cls) -> TasaCambioPort:
        from ventas.infra.externos.tasa_cambio import ExchangeRateApiAdapter, TasaCambioConRespaldo, TasaCambioFija
        return cls._o("tasa_cambio", lambda: TasaCambioConRespaldo(
            principal=ExchangeRateApiAdapter(settings.TASA_CAMBIO_API_URL),
            respaldo=TasaCambioFija(Decimal(settings.TASA_COP_USD_RESPALDO))))

    @classmethod
    def aliado(cls) -> ServicioAliadoPort:
        from ventas.infra.externos.aliado import AliadoHttpAdapter
        return cls._o("aliado", lambda: AliadoHttpAdapter(settings.ALIADO_NOMBRE, settings.ALIADO_API_URL))

    @classmethod
    def cola_tareas(cls) -> ColaTareasPort:
        from ventas.infra.mensajeria.cola_celery import ColaTareasCelery
        return cls._o("cola_tareas", ColaTareasCelery)
