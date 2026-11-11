"""Traduce errores a respuestas JSON con la forma {"error": ..., "codigo": ...}."""
from flask import Flask, jsonify

from app.dominio.errores import ErrorFabricacion
from app.i18n import _


def registrar_manejadores(app: Flask) -> None:
    @app.errorhandler(ErrorFabricacion)
    def _error_fabricacion(error: ErrorFabricacion):
        return jsonify({"error": error.mensaje, "codigo": error.codigo}), error.status

    @app.errorhandler(404)
    def _no_encontrado(_e):
        return jsonify({"error": _("Recurso no encontrado."), "codigo": "NO_ENCONTRADO"}), 404

    @app.errorhandler(405)
    def _metodo(_e):
        return jsonify({"error": _("Método no permitido."), "codigo": "METODO_NO_PERMITIDO"}), 405

    @app.errorhandler(500)
    def _interno(_e):
        return jsonify({"error": _("Error interno del servicio."), "codigo": "ERROR_INTERNO"}), 500
