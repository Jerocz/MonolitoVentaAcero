from flask import Blueprint, jsonify

from app.dominio.etapas import SECUENCIA_ETAPAS
from app.rutas.comun import PREFIJO
from app.serializadores import etapa_json

bp = Blueprint("etapas", __name__, url_prefix=PREFIJO)


@bp.get("/etapas")
def etapas():
    return jsonify([etapa_json(e) for e in SECUENCIA_ETAPAS])
