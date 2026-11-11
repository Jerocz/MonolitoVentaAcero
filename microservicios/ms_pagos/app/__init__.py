"""Microservicio de Pagos (extraido del monolito con el Strangler Pattern).

Responsabilidades migradas desde Django:
  - Pasarelas de pago real/mock y su Factory (antes: ventas/infra/).
  - Calculo del anticipo (50%) y del saldo final (antes: services.py).
  - Registro de cobros (antes: modelo Pago).
"""
import os

from flask import Flask, jsonify

from app.db import BaseDeDatos
from app.i18n import _
from app.infra.pasarelas import PasarelaPago, PasarelaPagoFactory


def create_app(database_url: str | None = None, pasarela: PasarelaPago | None = None) -> Flask:
    app = Flask(__name__)
    app.json.sort_keys = False
    app.json.ensure_ascii = False
    url = database_url or os.getenv("DATABASE_URL", "sqlite:///pagos.sqlite3")
    db = BaseDeDatos(url)
    app.extensions["db"] = db
    # Inyeccion de dependencias: las pruebas pueden pasar su propia pasarela.
    app.extensions["pasarela"] = pasarela or PasarelaPagoFactory.crear()

    from app import modelos  # noqa: F401
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
