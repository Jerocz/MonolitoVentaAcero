"""Pasarelas de pago: una real y una simulada (mock), con el mismo contrato."""
import uuid
from abc import ABC, abstractmethod
from decimal import Decimal


class ResultadoPago:
    def __init__(self, aprobado, referencia):
        self.aprobado = aprobado
        self.referencia = referencia


class PasarelaPago(ABC):
    @abstractmethod
    def cobrar(self, monto: Decimal, email_cliente: str) -> ResultadoPago:
        ...


class PasarelaReal(PasarelaPago):
    def cobrar(self, monto, email_cliente):
        referencia = f"REAL-{uuid.uuid4().hex[:12]}"
        return ResultadoPago(aprobado=monto > 0, referencia=referencia)


class PasarelaMock(PasarelaPago):
    def cobrar(self, monto, email_cliente):
        referencia = f"MOCK-{uuid.uuid4().hex[:12]}"
        return ResultadoPago(aprobado=True, referencia=referencia)
