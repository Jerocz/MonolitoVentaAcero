"""Consultas de cobros y del estado de pago de varias cotizaciones."""
from flask import Blueprint, jsonify, request

from app.rutas.comun import PREFIJO, db, servicio
from app.serializadores import cobro_json, estado_json

bp = Blueprint("consultas", __name__, url_prefix=PREFIJO)


@bp.get("/cobros")
def listar_cobros():
    with db().sesion() as s:
        return jsonify([cobro_json(c) for c in servicio(s).historial(request.args.get("concepto_ref"))])


@bp.get("/estado")
def estado():
    """Estado de pago de varias cotizaciones a la vez: ?refs=COT-1,COT-2"""
    refs = [r.strip() for r in request.args.get("refs", "").split(",") if r.strip()][:100]
    with db().sesion() as s:
        return jsonify(estado_json(servicio(s).estado(refs)))
