"""Conversion de modelos a JSON (contrato de la API)."""
from decimal import Decimal

from app.modelos import Cobro


def dinero(valor) -> str:
    return str(Decimal(valor).quantize(Decimal("0.01")))


def cobro_json(c: Cobro) -> dict:
    return {
        "id": c.id,
        "concepto_ref": c.concepto_ref,
        "tipo": c.tipo,
        "monto": dinero(c.monto),
        "aprobado": c.aprobado,
        "referencia": c.referencia,
        "pasarela": c.pasarela,
        "creado": c.creado.isoformat(timespec="seconds") if c.creado else None,
    }


def estado_json(estado: dict) -> dict:
    return {ref: {**fila, "total_pagado": dinero(fila["total_pagado"])} for ref, fila in estado.items()}
