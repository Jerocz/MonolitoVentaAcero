"""Rutas HTTP del microservicio, un archivo por recurso (prefijo /api/catalogo).

    salud.py         GET  /health
    productos.py     GET/POST /productos
    cotizaciones.py  POST /cotizaciones/simular
    reservas.py      POST /reservas, /reservas/<ref>/liberar
    publico.py       GET  /publico/v1/productos  (servicio para el equipo aliado)
"""
from app.rutas import cotizaciones, productos, publico, reservas, salud

BLUEPRINTS = [salud.bp, productos.bp, cotizaciones.bp, reservas.bp, publico.bp]
