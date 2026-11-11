"""Modelos persistentes del microservicio de catalogo."""
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _ahora():
    return datetime.now(timezone.utc)


class Producto(Base):
    __tablename__ = "productos"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    tipo: Mapped[str] = mapped_column(String(10))
    calibre_acero: Mapped[int] = mapped_column(Integer)
    precio_base_m2: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    # m2 disponibles para productos a la medida; unidades para productos estandar.
    stock_m2: Mapped[Decimal] = mapped_column(Numeric(10, 2))


class Reserva(Base):
    """Stock apartado para una cotizacion. Se puede liberar (compensacion)."""
    __tablename__ = "reservas"

    ACTIVA = "ACTIVA"
    LIBERADA = "LIBERADA"

    id: Mapped[int] = mapped_column(primary_key=True)
    referencia: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    estado: Mapped[str] = mapped_column(String(10), default=ACTIVA)
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    creada: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_ahora)
    lineas: Mapped[list["LineaReserva"]] = relationship(
        back_populates="reserva", cascade="all, delete-orphan", lazy="selectin")


class LineaReserva(Base):
    __tablename__ = "lineas_reserva"

    id: Mapped[int] = mapped_column(primary_key=True)
    reserva_id: Mapped[int] = mapped_column(ForeignKey("reservas.id"))
    producto_id: Mapped[int] = mapped_column(ForeignKey("productos.id"))
    producto_nombre: Mapped[str] = mapped_column(String(120))
    producto_tipo: Mapped[str] = mapped_column(String(10))
    ancho_cm: Mapped[Decimal] = mapped_column(Numeric(6, 1))
    largo_cm: Mapped[Decimal] = mapped_column(Numeric(6, 1))
    cantidad: Mapped[int] = mapped_column(Integer)
    consumo_stock: Mapped[Decimal] = mapped_column(Numeric(10, 4))
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    reserva: Mapped[Reserva] = relationship(back_populates="lineas")
