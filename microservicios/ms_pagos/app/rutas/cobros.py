"""Cobro del anticipo (paso 3 de la saga) y del saldo final."""
from flask import Blueprint, jsonify

from app.rutas.comun import PREFIJO, datos_cobro, db, servicio
from app.serializadores import cobro_json

bp = Blueprint("cobros", __name__, url_prefix=PREFIJO)


def _respuesta(cobro, es_nuevo):
    # 200 = ya estaba cobrado (idempotencia); 201 = cobrado ahora;
    # 402 Payment Required = la pasarela lo rechazo (queda registrado).
    if not es_nuevo:
        return jsonify(cobro_json(cobro)), 200
    return jsonify(cobro_json(cobro)), (201 if cobro.aprobado else 402)


@bp.post("/anticipos")
def cobrar_anticipo():
    concepto, total, email = datos_cobro()
    with db().sesion() as s:
        return _respuesta(*servicio(s).anticipo(concepto, total, email))


@bp.post("/saldos")
def cobrar_saldo():
    concepto, total, email = datos_cobro()
    with db().sesion() as s:
        return _respuesta(*servicio(s).saldo(concepto, total, email))
