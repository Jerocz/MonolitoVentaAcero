"""Configuracion del microservicio (leida de variables de entorno)."""
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    database_url: str
    nombre_servicio: str = "ms-catalogo"
    proveedor: str = "Integrales Torres B."

    @classmethod
    def desde_entorno(cls) -> "Config":
        return cls(database_url=os.getenv("DATABASE_URL", "sqlite:///catalogo.sqlite3"))
