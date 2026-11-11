"""Utilidades compartidas por las rutas."""
from flask import current_app, request

from app.dominio.errores import SolicitudInvalidaError
from app.i18n import _

PREFIJO = "/api/catalogo"


def db():
    return current_app.extensions["db"]


def json_entrada() -> dict:
    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        raise SolicitudInvalidaError(_("El cuerpo debe ser un objeto JSON."), "JSON_INVALIDO")
    return datos
