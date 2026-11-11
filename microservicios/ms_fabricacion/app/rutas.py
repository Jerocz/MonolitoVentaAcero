"""API HTTP del microservicio de fabricacion (JSON)."""
from decimal import Decimal, InvalidOperation

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import select

from app.dominio.etapas import (
    SECUENCIA_ETAPAS,
    EtapaFinalError,
    etapa_inicial,
    fecha_estimada,
    progreso,
    siguiente_etapa,
)
from app.i18n import _
from app.modelos import EventoOrden, Orden

bp = Blueprint("fabricacion", __name__, url_prefix="/api/fabricacion")


def _db():
    return current_app.extensions["db"]


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


def orden_json(o: Orden, con_eventos=False) -> dict:
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
        datos["eventos"] = [{"estado": e.estado, "estado_display": nombre_etapa(e.estado),
                             "fecha": e.fecha.isoformat(timespec="seconds")} for e in o.eventos]
    return datos


def _error(status, codigo, mensaje):
    return jsonify({"error": mensaje, "codigo": codigo}), status


@bp.get("/health")
def salud():
    with _db().sesion() as s:
        s.execute(select(1))
    return jsonify({"servicio": "ms-fabricacion", "estado": "ok"})


@bp.get("/etapas")
def etapas():
    return jsonify([{"estado": e, "estado_display": nombre_etapa(e)} for e in SECUENCIA_ETAPAS])


@bp.post("/ordenes")
def crear_orden():
    """Abre una orden para una cotizacion aprobada. Idempotente por cotizacion_ref
    (permite reintentos seguros desde la cola de tareas)."""
    datos = request.get_json(silent=True) or {}
    try:
        ref = str(datos["cotizacion_ref"]).strip()
        cliente = str(datos["cliente"]).strip()
        total = Decimal(str(datos["total"]))
    except (KeyError, InvalidOperation, ValueError, TypeError):
        return _error(400, "ORDEN_INVALIDA", _("Se requieren cotizacion_ref, cliente y total."))
    if not ref or not cliente or total <= 0:
        return _error(400, "ORDEN_INVALIDA", _("Se requieren cotizacion_ref, cliente y total."))

    with _db().sesion() as s:
        existente = s.scalar(select(Orden).where(Orden.cotizacion_ref == ref))
        if existente:
            return jsonify(orden_json(existente)), 200
        orden = Orden(cotizacion_ref=ref, cliente=cliente, total=total,
                      estado=etapa_inicial(), fecha_estimada_entrega=fecha_estimada())
        orden.eventos.append(EventoOrden(estado=orden.estado))
        s.add(orden)
        s.flush()
        return jsonify(orden_json(orden)), 201


@bp.get("/ordenes")
def listar_ordenes():
    try:
        limite = max(1, min(int(request.args.get("limit", 20)), 200))
    except ValueError:
        limite = 20
    with _db().sesion() as s:
        ordenes = s.scalars(select(Orden).order_by(Orden.id.desc()).limit(limite)).all()
        return jsonify([orden_json(o) for o in ordenes])


@bp.get("/ordenes/<int:orden_id>")
def obtener_orden(orden_id):
    with _db().sesion() as s:
        orden = s.get(Orden, orden_id)
        if orden is None:
            return _error(404, "ORDEN_NO_EXISTE", _("La orden {id} no existe.", id=orden_id))
        return jsonify(orden_json(orden, con_eventos=True))


@bp.post("/ordenes/<int:orden_id>/avanzar")
def avanzar(orden_id):
    with _db().sesion() as s:
        orden = s.get(Orden, orden_id, with_for_update=True)
        if orden is None:
            return _error(404, "ORDEN_NO_EXISTE", _("La orden {id} no existe.", id=orden_id))
        try:
            orden.estado = siguiente_etapa(orden.estado)
        except EtapaFinalError:
            return _error(409, "ORDEN_ENTREGADA", _("La orden {id} ya fue entregada.", id=orden_id))
        orden.eventos.append(EventoOrden(estado=orden.estado))
        s.flush()
        return jsonify(orden_json(orden, con_eventos=True))
