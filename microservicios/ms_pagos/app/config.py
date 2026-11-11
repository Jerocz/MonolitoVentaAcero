"""Configuracion del microservicio (leida de variables de entorno)."""
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    database_url: str
    tipo_pasarela: str          # MOCK o REAL (lo usa PasarelaPagoFactory)
    nombre_servicio: str = "ms-pagos"

    @classmethod
    def desde_entorno(cls) -> "Config":
        return cls(database_url=os.getenv("DATABASE_URL", "sqlite:///pagos.sqlite3"),
                   tipo_pasarela=os.getenv("ENV_TYPE", "MOCK").upper())
