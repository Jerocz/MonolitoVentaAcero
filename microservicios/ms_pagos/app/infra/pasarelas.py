"""Pasarelas de pago (migradas desde ventas/infra/pasarelas.py) + Factory.

Mismo contrato para la pasarela real y la simulada; la Factory elige segun
la variable de entorno ENV_TYPE (MOCK por defecto).
"""
import os
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ResultadoPago:
    aprobado: bool
    referencia: str


class PasarelaPago(ABC):
    nombre = "abstracta"

    @abstractmethod
    def cobrar(self, monto: Decimal, email_cliente: str) -> ResultadoPago:
        ...


class PasarelaReal(PasarelaPago):
    nombre = "PasarelaReal"

    def cobrar(self, monto, email_cliente):
        return ResultadoPago(aprobado=monto > 0, referencia=f"REAL-{uuid.uuid4().hex[:12]}")


class PasarelaMock(PasarelaPago):
    """Aprueba todo, salvo correos del dominio de prueba `rechazo.test`
    (sirve para demostrar la compensacion de la saga en la sustentacion)."""
    nombre = "PasarelaMock"
    DOMINIO_RECHAZO = "@rechazo.test"

    def cobrar(self, monto, email_cliente):
        aprobado = not email_cliente.lower().endswith(self.DOMINIO_RECHAZO)
        return ResultadoPago(aprobado=aprobado, referencia=f"MOCK-{uuid.uuid4().hex[:12]}")


class PasarelaPagoFactory:
    @staticmethod
    def crear() -> PasarelaPago:
        if os.getenv("ENV_TYPE", "MOCK").upper() == "REAL":
            return PasarelaReal()
        return PasarelaMock()
