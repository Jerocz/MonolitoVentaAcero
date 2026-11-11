"""Service Layer del monolito.

    cotizacion.py  CotizacionService: saga orquestada para crear una cotizacion
    ordenes.py     OrdenService: avance de etapas y pago del saldo
"""
from ventas.services.cotizacion import CotizacionService
from ventas.services.ordenes import OrdenService

__all__ = ["CotizacionService", "OrdenService"]
