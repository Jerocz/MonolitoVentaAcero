"""Crea las tablas y carga el catalogo inicial. Uso: python -m app.init_db"""
import os
import time
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError

from app.db import BaseDeDatos
from app.modelos import Producto

CATALOGO_INICIAL = [
    ("Lamina 304", "LAMINA", 304, Decimal("120000"), Decimal("60")),
    ("Meson central", "MESON", 304, Decimal("120000"), Decimal("60")),
    ("Campana extractora", "CAMPANA", 430, Decimal("90000"), Decimal("60")),
    ("Freidora 2 canastas", "FREIDORA", 304, Decimal("1500000"), Decimal("99")),
]


def inicializar(db: BaseDeDatos):
    for intento in range(10):  # la base de datos puede tardar en aceptar conexiones
        try:
            db.crear_tablas()
            break
        except OperationalError:
            time.sleep(2 + intento)
    with db.sesion() as s:
        if s.scalar(select(func.count(Producto.id))) == 0:
            for nombre, tipo, calibre, precio, stock in CATALOGO_INICIAL:
                s.add(Producto(nombre=nombre, tipo=tipo, calibre_acero=calibre,
                               precio_base_m2=precio, stock_m2=stock))
            print("Catalogo inicial cargado.")


if __name__ == "__main__":
    inicializar(BaseDeDatos(os.getenv("DATABASE_URL", "sqlite:///catalogo.sqlite3")))
