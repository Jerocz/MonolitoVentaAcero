"""Constantes y reglas del negocio (datos de dominio, sin logica de modelos)."""
from decimal import Decimal

from ventas.models import OrdenFabricacion

# Secuencia de etapas de fabricacion, en orden.
SECUENCIA_ETAPAS = [
    OrdenFabricacion.Estado.EN_COLA,
    OrdenFabricacion.Estado.CORTE,
    OrdenFabricacion.Estado.SOLDADURA,
    OrdenFabricacion.Estado.PULIDO,
    OrdenFabricacion.Estado.TERMINADA,
    OrdenFabricacion.Estado.ENTREGADA,
]

FRACCION_ANTICIPO = Decimal("0.5")
DIAS_VIGENCIA_COTIZACION = 15
DIAS_FABRICACION = 20
