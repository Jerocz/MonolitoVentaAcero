"""DTOs del dominio: los datos que viajan entre los servicios del monolito y los
adaptadores. Son inmutables y no dependen de Django ni de ningun microservicio."""
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal


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
