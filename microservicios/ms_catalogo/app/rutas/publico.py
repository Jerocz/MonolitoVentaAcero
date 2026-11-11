"""Servicio que PROVEEMOS al equipo aliado: catalogo vigente con precios y stock."""
from datetime import datetime, timezone

from flask import Blueprint, current_app, jsonify
from sqlalchemy import select

from app.i18n import _, idioma_actual
from app.modelos import Producto
from app.rutas.comun import PREFIJO, db
from app.serializadores import producto_publico_json

bp = Blueprint("publico", __name__, url_prefix=PREFIJO)


@bp.get("/publico/v1/productos")
def publico_productos():
    with db().sesion() as s:
        productos = s.scalars(select(Producto).order_by(Producto.id)).all()
        return jsonify({
            "proveedor": current_app.config["PROVEEDOR"],
            "descripcion": _("Catálogo de productos en acero inoxidable fabricados a la medida."),
            "moneda": "COP",
            "idioma": idioma_actual(),
            "generado_en": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "total_productos": len(productos),
            "productos": [producto_publico_json(p) for p in productos],
        })
