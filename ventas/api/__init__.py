"""API REST del monolito (DRF). Solo traduce HTTP <-> servicios y devuelve el
codigo de estado correcto; sin logica de negocio.

    serializadores.py  validacion de entrada y formato de salida
    respuestas.py      respuestas comunes (503, orden en JSON)
    cotizaciones.py, catalogo.py, ordenes.py, integraciones.py  endpoints
"""
from ventas.api.catalogo import ProductoListAPIView
from ventas.api.cotizaciones import CrearCotizacionAPIView
from ventas.api.integraciones import AliadoAPIView, TasaCambioAPIView
from ventas.api.ordenes import AvanzarEtapaAPIView, PagarSaldoAPIView

__all__ = ["AliadoAPIView", "AvanzarEtapaAPIView", "CrearCotizacionAPIView", "PagarSaldoAPIView",
           "ProductoListAPIView", "TasaCambioAPIView"]
