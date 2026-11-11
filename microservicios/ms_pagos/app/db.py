"""Persistencia propia del microservicio (Database per Service).

Cada microservicio es duenio de su base de datos: nadie mas la lee ni la
escribe directamente; los demas componentes solo hablan con el por HTTP.
"""
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import StaticPool


class Base(DeclarativeBase):
    pass


def crear_engine(url: str):
    if url.startswith("sqlite"):
        # StaticPool: una sola conexion compartida (necesario para sqlite en memoria en pruebas).
        return create_engine(url, connect_args={"check_same_thread": False}, poolclass=StaticPool)
    return create_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=5)


class BaseDeDatos:
    def __init__(self, url: str):
        self.engine = crear_engine(url)
        self._fabrica = sessionmaker(bind=self.engine, expire_on_commit=False)

    def crear_tablas(self):
        Base.metadata.create_all(self.engine)

    @contextmanager
    def sesion(self):
        """Unidad de trabajo: commit si todo sale bien, rollback si algo falla."""
        sesion = self._fabrica()
        try:
            yield sesion
            sesion.commit()
        except Exception:
            sesion.rollback()
            raise
        finally:
            sesion.close()
