"""Puertos (interfaces) del dominio - Inversion de Dependencias.

Los servicios del monolito dependen de estas abstracciones, NO de los
microservicios, de `requests` ni de una API de terceros concreta. Las
implementaciones (adaptadores) viven en `ventas/infra/` y se inyectan desde
`ventas/infra/contenedor.py`; en las pruebas se inyectan dobles en memoria.

    services/  --->  puertos.py  <---  infra/microservicios/, infra/externos/
    (alto nivel)    (abstraccion)      infra/mensajeria/ (bajo nivel)

Los datos que intercambian estan en `ventas/domain/dtos.py`.
"""
from abc import ABC, abstractmethod
from decimal import Decimal

from ventas.domain.dtos import (
    CobroDTO,
    EstadoPagoDTO,
    InfoAliadoDTO,
    OrdenDTO,
    ProductoDTO,
    ReservaDTO,
    TasaCambioDTO,
)


class CatalogoPort(ABC):
    @abstractmethod
    def listar_productos(self) -> list[ProductoDTO]: ...

    @abstractmethod
    def reservar(self, referencia: str, items: list[dict]) -> ReservaDTO:
        """Valida reglas, calcula precios y aparta stock (idempotente por referencia)."""

    @abstractmethod
    def liberar(self, referencia: str) -> None:
        """Compensacion: devuelve el stock de la reserva."""


class PagosPort(ABC):
    @abstractmethod
    def cobrar_anticipo(self, referencia: str, total: Decimal, email: str) -> CobroDTO: ...

    @abstractmethod
    def cobrar_saldo(self, referencia: str, total: Decimal, email: str) -> CobroDTO: ...

    @abstractmethod
    def estado(self, referencias: list[str]) -> dict[str, EstadoPagoDTO]: ...


class FabricacionPort(ABC):
    @abstractmethod
    def crear_orden(self, referencia: str, cliente: str, total: Decimal) -> OrdenDTO: ...

    @abstractmethod
    def listar_ordenes(self, limite: int = 8) -> list[OrdenDTO]: ...

    @abstractmethod
    def obtener(self, orden_id: int) -> OrdenDTO: ...

    @abstractmethod
    def avanzar(self, orden_id: int) -> OrdenDTO: ...

    @abstractmethod
    def etapas(self) -> list[str]: ...


class TasaCambioPort(ABC):
    """Puerto hacia la API de TERCEROS de tasas de cambio."""

    @abstractmethod
    def obtener(self, origen: str = "COP", destino: str = "USD") -> TasaCambioDTO: ...


class ServicioAliadoPort(ABC):
    """Puerto hacia el servicio que expone el equipo aliado."""

    @abstractmethod
    def consultar(self) -> InfoAliadoDTO: ...


class ColaTareasPort(ABC):
    """Puerto hacia el Message Broker (procesos en segundo plano)."""

    @abstractmethod
    def notificar_cotizacion_aprobada(self, cotizacion_id: int) -> None: ...

    @abstractmethod
    def notificar_cambio_etapa(self, cotizacion_ref: str, estado_display: str) -> None: ...

    @abstractmethod
    def programar_creacion_orden(self, cotizacion_id: int) -> None: ...

    @abstractmethod
    def generar_reporte(self, reporte_id: int) -> None: ...
