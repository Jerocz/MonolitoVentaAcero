"""Utilidades compartidas por las rutas."""
from flask import current_app

PREFIJO = "/api/fabricacion"


def db():
    return current_app.extensions["db"]
