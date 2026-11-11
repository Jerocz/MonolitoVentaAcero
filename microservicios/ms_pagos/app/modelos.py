"""Modelos persistentes del microservicio de pagos."""
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def _ahora():
    return datetime.now(timezone.utc)


class Cobro(Base):
    """Un intento de cobro ante la pasarela (aprobado o rechazado)."""
    __tablename__ = "cobros"

    ANTICIPO = "ANTICIPO"
    SALDO = "SALDO"

    id: Mapped[int] = mapped_column(primary_key=True)
    concepto_ref: Mapped[str] = mapped_column(String(40), index=True)  # p. ej. COT-12
    tipo: Mapped[str] = mapped_column(String(10))
    monto: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    email: Mapped[str] = mapped_column(String(254))
    aprobado: Mapped[bool] = mapped_column(Boolean, default=False)
    referencia: Mapped[str] = mapped_column(String(64))
    pasarela: Mapped[str] = mapped_column(String(30))
    creado: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_ahora)
