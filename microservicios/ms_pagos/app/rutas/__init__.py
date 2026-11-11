"""Rutas HTTP del microservicio, un archivo por recurso (prefijo /api/pagos).

    salud.py      GET  /health
    cobros.py     POST /anticipos, POST /saldos
    consultas.py  GET  /cobros, GET /estado
"""
from app.rutas import cobros, consultas, salud

BLUEPRINTS = [salud.bp, cobros.bp, consultas.bp]
