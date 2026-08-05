"""Patron Factory: elige la pasarela segun la variable de entorno ENV_TYPE."""
import os

from ventas.infra.pasarelas import PasarelaMock, PasarelaPago, PasarelaReal


class PasarelaPagoFactory:
    @staticmethod
    def crear() -> PasarelaPago:
        if os.getenv("ENV_TYPE", "MOCK").upper() == "REAL":
            return PasarelaReal()
        return PasarelaMock()
