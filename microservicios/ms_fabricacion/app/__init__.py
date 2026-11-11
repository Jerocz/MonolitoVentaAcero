"""Microservicio de Fabricacion (extraido del monolito con el Strangler Pattern).

Responsabilidades migradas desde Django:
  - Ordenes de fabricacion (antes: modelo OrdenFabricacion).
  - Secuencia de etapas y su avance (antes: reglas.py / OrdenService.avanzar_etapa).
  - Historial de cambios de etapa (nuevo: trazabilidad).

Estructura:
    config.py          configuracion desde variables de entorno
    db.py              motor y unidad de trabajo (SQLAlchemy)
    modelos.py         ordenes y eventos
    dominio/           secuencia de etapas y errores
    servicios.py       casos de uso (crear, listar, avanzar)
    serializadores.py  modelos -> JSON
    rutas/             endpoints HTTP, un archivo por recurso
    errores_http.py    traduccion de errores a respuestas JSON
    i18n.py            traducciones gettext (es/en)
"""
from flask import Flask

from app.config import Config
from app.db import BaseDeDatos
from app.errores_http import registrar_manejadores


def create_app(database_url: str | None = None) -> Flask:
    config = Config.desde_entorno()
    url = database_url or config.database_url

    app = Flask(__name__)
    app.json.sort_keys = False
    app.json.ensure_ascii = False
    app.config.update(SERVICIO=config.nombre_servicio)

    db = BaseDeDatos(url)
    app.extensions["db"] = db

    from app import modelos  # noqa: F401
    from app.rutas import BLUEPRINTS
    for bp in BLUEPRINTS:
        app.register_blueprint(bp)
    registrar_manejadores(app)

    if url.startswith("sqlite"):
        db.crear_tablas()
    return app
