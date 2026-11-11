"""Puertos (interfaces) del dominio - Inversion de Dependencias.

Los servicios del monolito dependen de estas abstracciones, NO de los
microservicios, de `requests` ni de una API de terceros concreta. Las
implementaciones (adaptadores) viven en `ventas/infra/` y se inyectan desde
`ventas/infra/contenedor.py`; en las pruebas se inyectan dobles en memoria.

    services.py  --->  puertos.py  <---  infra/adaptadores_http.py
     (alto nivel)     (abstraccion)       infra/terceros.py (bajo nivel)
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal


# --------------------------------------------------------------------- DTOs
@dataclass(frozen=True)
class ProductoDTO:
    id: int
    nombre: str
    tipo: str
    tipo_display: str
    calibre_acero: int
    precio_base_m2: Decimal
    stock_m2: Decimal
    es_a_medida: bool
    unidad: str
    ancho_minimo_cm: Decimal | None = None


@dataclass(frozen=True)
class LineaReservadaDTO:
    producto_id: int
    producto_nombre: str
    producto_tipo: str
    ancho_cm: Decimal
    largo_cm: Decimal
    cantidad: int
    subtotal: Decimal


@dataclass(frozen=True)
class ReservaDTO:
    referencia: str
    total: Decimal
    lineas: list[LineaReservadaDTO]


@dataclass(frozen=True)
class CobroDTO:
    aprobado: bool
    monto: Decimal
    referencia: str


@dataclass(frozen=True)
class EstadoPagoDTO:
    anticipo_pagado: bool = False
    saldo_pagado: bool = False


@dataclass(frozen=True)
class OrdenDTO:
    id: int
    cotizacion_ref: str
    cliente: str
    total: Decimal
    estado: str
    estado_display: str
    indice_etapa: int
    progreso: int
    fecha_estimada_entrega: date


@dataclass(frozen=True)
class TasaCambioDTO:
    origen: str
    destino: str
    valor: Decimal          # 1 unidad de `origen` = `valor` unidades de `destino`
    fuente: str
    actualizada: datetime | None = None
    es_respaldo: bool = False

    def convertir(self, monto: Decimal) -> Decimal:
        return (Decimal(monto) * self.valor).quantize(Decimal("0.01"))


@dataclass(frozen=True)
class InfoAliadoDTO:
    nombre: str
    disponible: bool
    url: str = ""
    elementos: list[dict] = field(default_factory=list)
    mensaje: str = ""


# ------------------------------------------------------------------- Puertos
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
