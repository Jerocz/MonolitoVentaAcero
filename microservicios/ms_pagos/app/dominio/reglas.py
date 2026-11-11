"""Reglas de cobro (migradas desde CotizacionService.calcular_anticipo y
OrdenService.pagar_saldo del monolito)."""
from decimal import Decimal

FRACCION_ANTICIPO = Decimal("0.5")
CENTAVOS = Decimal("0.01")


def calcular_anticipo(total: Decimal) -> Decimal:
    return (Decimal(total) * FRACCION_ANTICIPO).quantize(CENTAVOS)


def calcular_saldo(total: Decimal) -> Decimal:
    return (Decimal(total) - calcular_anticipo(total)).quantize(CENTAVOS)
