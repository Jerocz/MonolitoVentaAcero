"""Utilidades compartidas por las rutas."""
from decimal import Decimal, InvalidOperation

from flask import current_app, request

from app.dominio.errores import ErrorPagos
from app.i18n import _
from app.servicios import ServicioCobros

PREFIJO = "/api/pagos"


def db():
    return current_app.extensions["db"]


def pasarela():
    return current_app.extensions["pasarela"]


def servicio(sesion) -> ServicioCobros:
    return ServicioCobros(sesion, pasarela())


def datos_cobro() -> tuple[str, Decimal, str]:
    """Valida el cuerpo {concepto_ref, total, email} de una solicitud de cobro."""
    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        raise ErrorPagos(400, "JSON_INVALIDO", _("El cuerpo debe ser un objeto JSON."))
    invalido = ErrorPagos(400, "COBRO_INVALIDO", _("Se requieren concepto_ref, total y email."))
    try:
        concepto = str(datos["concepto_ref"]).strip()
        total = Decimal(str(datos["total"]))
        email = str(datos["email"]).strip()
    except (KeyError, InvalidOperation, ValueError):
        raise invalido
    if not concepto or total <= 0 or "@" not in email:
        raise invalido
    return concepto, total, email
