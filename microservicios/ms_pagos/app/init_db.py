"""Crea las tablas del microservicio. Uso: python -m app.init_db"""
import time

from sqlalchemy.exc import OperationalError

from app import modelos  # noqa: F401
from app.config import Config
from app.db import BaseDeDatos


def inicializar(db: BaseDeDatos):
    for intento in range(10):
        try:
            db.crear_tablas()
            return
        except OperationalError:
            time.sleep(2 + intento)
    raise RuntimeError("No fue posible conectar con la base de datos de pagos.")


if __name__ == "__main__":
    inicializar(BaseDeDatos(Config.desde_entorno().database_url))
