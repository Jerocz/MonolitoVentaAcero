"""Rutas HTTP del microservicio, un archivo por recurso (prefijo /api/fabricacion).

    salud.py    GET  /health
    etapas.py   GET  /etapas
    ordenes.py  POST /ordenes, GET /ordenes, GET /ordenes/<id>, POST /ordenes/<id>/avanzar
"""
from app.rutas import etapas, ordenes, salud

BLUEPRINTS = [salud.bp, etapas.bp, ordenes.bp]
