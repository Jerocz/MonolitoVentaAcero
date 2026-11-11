"""Rutas de la API REST del monolito (prefijo /api/)."""
from django.urls import path

from ventas.api import (
    AliadoAPIView,
    AvanzarEtapaAPIView,
    CrearCotizacionAPIView,
    PagarSaldoAPIView,
    ProductoListAPIView,
    TasaCambioAPIView,
)

urlpatterns = [
    path("productos/", ProductoListAPIView.as_view(), name="api_productos"),
    path("cotizaciones/", CrearCotizacionAPIView.as_view(), name="api_crear_cotizacion"),
    path("ordenes/<int:orden_id>/avanzar/", AvanzarEtapaAPIView.as_view(), name="api_avanzar"),
    path("ordenes/<int:orden_id>/saldo/", PagarSaldoAPIView.as_view(), name="api_saldo"),
    path("integraciones/tasa-cambio/", TasaCambioAPIView.as_view(), name="api_tasa_cambio"),
    path("integraciones/aliado/", AliadoAPIView.as_view(), name="api_aliado"),
]
