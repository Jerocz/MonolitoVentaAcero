"""Modelos persistentes del microservicio de fabricacion."""
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _ahora():
    return datetime.now(timezone.utc)


class Orden(Base):
    __tablename__ = "ordenes"

    id: Mapped[int] = mapped_column(primary_key=True)
    cotizacion_ref: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    cliente: Mapped[str] = mapped_column(String(120))
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    estado: Mapped[str] = mapped_column(String(10))
    fecha_estimada_entrega: Mapped[date] = mapped_column(Date)
    creada: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_ahora)
    eventos: Mapped[list["EventoOrden"]] = relationship(
        back_populates="orden", cascade="all, delete-orphan", lazy="selectin",
        order_by="EventoOrden.id")


class EventoOrden(Base):
    """Historial (trazabilidad) de cada cambio de etapa."""
    __tablename__ = "eventos_orden"

    id: Mapped[int] = mapped_column(primary_key=True)
    orden_id: Mapped[int] = mapped_column(ForeignKey("ordenes.id"))
    estado: Mapped[str] = mapped_column(String(10))
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_ahora)
    orden: Mapped[Orden] = relationship(back_populates="eventos")
