from flask import Blueprint, current_app, jsonify
from sqlalchemy import select

from app.rutas.comun import PREFIJO, db

bp = Blueprint("salud", __name__, url_prefix=PREFIJO)


@bp.get("/health")
def salud():
    with db().sesion() as s:
        s.execute(select(1))
    return jsonify({"servicio": current_app.config["SERVICIO"], "estado": "ok"})
