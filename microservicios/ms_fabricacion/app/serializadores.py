"""Conversion de modelos a JSON (contrato de la API)."""
from decimal import Decimal

from app.dominio.etapas import SECUENCIA_ETAPAS, progreso
from app.i18n import _
from app.modelos import Orden


def nombre_etapa(estado: str) -> str:
    nombres = {
        "EN_COLA": _("En cola"),
        "CORTE": _("Corte"),
        "SOLDADURA": _("Soldadura"),
        "PULIDO": _("Pulido"),
        "TERMINADA": _("Terminada"),
        "ENTREGADA": _("Entregada"),
    }
    return nombres.get(estado, estado)


def etapa_json(estado: str) -> dict:
    return {"estado": estado, "estado_display": nombre_etapa(estado)}


def orden_json(o: Orden, con_eventos: bool = False) -> dict:
    datos = {
        "id": o.id,
        "cotizacion_ref": o.cotizacion_ref,
        "cliente": o.cliente,
        "total": str(Decimal(o.total).quantize(Decimal("0.01"))),
        "estado": o.estado,
        "estado_display": nombre_etapa(o.estado),
        "indice_etapa": SECUENCIA_ETAPAS.index(o.estado),
        "progreso": progreso(o.estado),
        "fecha_estimada_entrega": o.fecha_estimada_entrega.isoformat(),
    }
    if con_eventos:
        datos["eventos"] = [etapa_json(e.estado) | {"fecha": e.fecha.isoformat(timespec="seconds")}
                            for e in o.eventos]
    return datos
