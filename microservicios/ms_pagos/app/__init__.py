"""Microservicio de Pagos (extraido del monolito con el Strangler Pattern).

Responsabilidades migradas desde Django:
  - Pasarelas de pago real/mock y su Factory (antes: ventas/infra/).
  - Calculo del anticipo (50%) y del saldo final (antes: services.py).
  - Registro de cobros (antes: modelo Pago).

Estructura:
    config.py          configuracion desde variables de entorno
    db.py              motor y unidad de trabajo (SQLAlchemy)
    modelos.py         tabla de cobros
    dominio/           reglas de cobro y errores
    infra/             pasarelas de pago + Factory
    servicios.py       casos de uso (anticipo, saldo, historial, estado)
    serializadores.py  modelos -> JSON
    rutas/             endpoints HTTP, un archivo por recurso
    errores_http.py    traduccion de errores a respuestas JSON
    i18n.py            traducciones gettext (es/en)
"""
from flask import Flask

from app.config import Config
from app.db import BaseDeDatos
from app.errores_http import registrar_manejadores
from app.infra.pasarelas import PasarelaPago, PasarelaPagoFactory


def create_app(database_url: str | None = None, pasarela: PasarelaPago | None = None) -> Flask:
    config = Config.desde_entorno()
    url = database_url or config.database_url

    app = Flask(__name__)
    app.json.sort_keys = False
    app.json.ensure_ascii = False
    app.config.update(SERVICIO=config.nombre_servicio)

    db = BaseDeDatos(url)
    app.extensions["db"] = db
    # Inyeccion de dependencias: las pruebas pueden pasar su propia pasarela.
    app.extensions["pasarela"] = pasarela or PasarelaPagoFactory.crear(config.tipo_pasarela)

    from app import modelos  # noqa: F401
    from app.rutas import BLUEPRINTS
    for bp in BLUEPRINTS:
        app.register_blueprint(bp)
    registrar_manejadores(app)

    if url.startswith("sqlite"):
        db.crear_tablas()
    return app
