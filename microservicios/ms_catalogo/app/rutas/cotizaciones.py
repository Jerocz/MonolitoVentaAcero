from decimal import Decimal

from flask import Blueprint, jsonify

from app.dominio.cotizador import cotizar, parsear_items
from app.modelos import Producto
from app.rutas.comun import PREFIJO, db, json_entrada
from app.serializadores import dinero, linea_cotizada_json

bp = Blueprint("cotizaciones", __name__, url_prefix=PREFIJO)


@bp.post("/cotizaciones/simular")
def simular():
    """Calcula precios y valida reglas SIN apartar stock."""
    items = parsear_items(json_entrada().get("items"))
    with db().sesion() as s:
        lineas = cotizar(items, lambda pid: s.get(Producto, pid))
        total = sum((l.subtotal for l in lineas), Decimal("0"))
        return jsonify({"total": dinero(total), "lineas": [linea_cotizada_json(l) for l in lineas]})
