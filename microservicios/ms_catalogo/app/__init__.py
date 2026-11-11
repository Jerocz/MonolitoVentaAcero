"""Microservicio de Catalogo y Precios (extraido del monolito con el Strangler Pattern).

Responsabilidades migradas desde Django:
  - Catalogo de productos y su stock (antes: modelos Producto/Lamina/Meson/...).
  - Estrategias de precio (antes: ventas/domain/precios.py).
  - Reglas de la cotizacion: ancho minimo, stock suficiente (antes: CotizacionBuilder).
  - Reserva y liberacion de stock (compensacion de la saga de cotizacion).
"""
import os

from flask import Flask, jsonify

from app.db import BaseDeDatos
from app.i18n import _


def create_app(database_url: str | None = None) -> Flask:
    app = Flask(__name__)
    app.json.sort_keys = False
    app.json.ensure_ascii = False
    url = database_url or os.getenv("DATABASE_URL", "sqlite:///catalogo.sqlite3")
    db = BaseDeDatos(url)
    app.extensions["db"] = db

    from app import modelos  # noqa: F401  (registra las tablas)
    from app.rutas import bp
    app.register_blueprint(bp)

    if url.startswith("sqlite"):
        db.crear_tablas()

    @app.errorhandler(404)
    def _no_encontrado(_e):
        return jsonify({"error": _("Recurso no encontrado."), "codigo": "NO_ENCONTRADO"}), 404

    @app.errorhandler(405)
    def _metodo(_e):
        return jsonify({"error": _("Método no permitido."), "codigo": "METODO_NO_PERMITIDO"}), 405

    @app.errorhandler(500)
    def _interno(_e):
        return jsonify({"error": _("Error interno del servicio."), "codigo": "ERROR_INTERNO"}), 500

    return app
