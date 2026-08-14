from django.urls import path

from ventas.api import (
    AvanzarEtapaAPIView,
    CrearCotizacionAPIView,
    PagarSaldoAPIView,
    ProductoListAPIView,
)
from ventas.views import (
    AvanzarEtapaWebView,
    CotizacionFormView,
    PagarSaldoWebView,
)

urlpatterns = [
    # --- Web (HTML, para la sustentacion) ---
    path("", CotizacionFormView.as_view(), name="cotizacion_form"),
    path("ordenes/<int:orden_id>/avanzar/", AvanzarEtapaWebView.as_view(), name="avanzar_etapa"),
    path("ordenes/<int:orden_id>/saldo/", PagarSaldoWebView.as_view(), name="pagar_saldo"),

    # --- API REST (DRF) ---
    path("api/productos/", ProductoListAPIView.as_view(), name="api_productos"),
    path("api/cotizaciones/", CrearCotizacionAPIView.as_view(), name="api_crear_cotizacion"),
    path("api/ordenes/<int:orden_id>/avanzar/", AvanzarEtapaAPIView.as_view(), name="api_avanzar"),
    path("api/ordenes/<int:orden_id>/saldo/", PagarSaldoAPIView.as_view(), name="api_saldo"),
]
