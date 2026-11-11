"""Ordenes de fabricacion (paso 4 de la saga) y su avance por etapas."""
from decimal import Decimal, InvalidOperation

from flask import Blueprint, jsonify, request

from app.dominio.errores import ErrorFabricacion
from app.i18n import _
from app.rutas.comun import PREFIJO, db
from app.serializadores import orden_json
from app.servicios import ServicioOrdenes

bp = Blueprint("ordenes", __name__, url_prefix=PREFIJO)


def _datos_orden() -> tuple[str, str, Decimal]:
    datos = request.get_json(silent=True) or {}
    invalida = ErrorFabricacion(400, "ORDEN_INVALIDA", _("Se requieren cotizacion_ref, cliente y total."))
    try:
        ref = str(datos["cotizacion_ref"]).strip()
        cliente = str(datos["cliente"]).strip()
        total = Decimal(str(datos["total"]))
    except (KeyError, InvalidOperation, ValueError, TypeError):
        raise invalida
    if not ref or not cliente or total <= 0:
        raise invalida
    return ref, cliente, total


@bp.post("/ordenes")
def crear_orden():
    ref, cliente, total = _datos_orden()
    with db().sesion() as s:
        orden, es_nueva = ServicioOrdenes(s).crear(ref, cliente, total)
        return jsonify(orden_json(orden)), (201 if es_nueva else 200)


@bp.get("/ordenes")
def listar_ordenes():
    try:
        limite = max(1, min(int(request.args.get("limit", 20)), 200))
    except ValueError:
        limite = 20
    with db().sesion() as s:
        return jsonify([orden_json(o) for o in ServicioOrdenes(s).listar(limite)])


@bp.get("/ordenes/<int:orden_id>")
def obtener_orden(orden_id):
    with db().sesion() as s:
        return jsonify(orden_json(ServicioOrdenes(s).obtener(orden_id), con_eventos=True))


@bp.post("/ordenes/<int:orden_id>/avanzar")
def avanzar(orden_id):
    with db().sesion() as s:
        return jsonify(orden_json(ServicioOrdenes(s).avanzar(orden_id), con_eventos=True))
