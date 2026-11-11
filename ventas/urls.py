from django.urls import path

from ventas.api import (
    AliadoAPIView,
    AvanzarEtapaAPIView,
    CrearCotizacionAPIView,
    PagarSaldoAPIView,
    ProductoListAPIView,
    TasaCambioAPIView,
)
from ventas.views import (
    AvanzarEtapaWebView,
    CotizacionFormView,
    IntegracionesView,
    PagarSaldoWebView,
    ProcesosView,
    salud,
    salud_viva,
)

urlpatterns = [
    # --- Web (HTML) ---
    path("", CotizacionFormView.as_view(), name="cotizacion_form"),
    path("ordenes/<int:orden_id>/avanzar/", AvanzarEtapaWebView.as_view(), name="avanzar_etapa"),
    path("ordenes/<int:orden_id>/saldo/", PagarSaldoWebView.as_view(), name="pagar_saldo"),
    path("integraciones/", IntegracionesView.as_view(), name="integraciones"),
    path("procesos/", ProcesosView.as_view(), name="procesos"),
    path("salud/", salud, name="salud"),
    path("salud/vivo/", salud_viva, name="salud_viva"),

    # --- API REST (DRF) del monolito ---
    path("api/productos/", ProductoListAPIView.as_view(), name="api_productos"),
    path("api/cotizaciones/", CrearCotizacionAPIView.as_view(), name="api_crear_cotizacion"),
    path("api/ordenes/<int:orden_id>/avanzar/", AvanzarEtapaAPIView.as_view(), name="api_avanzar"),
    path("api/ordenes/<int:orden_id>/saldo/", PagarSaldoAPIView.as_view(), name="api_saldo"),
    path("api/integraciones/tasa-cambio/", TasaCambioAPIView.as_view(), name="api_tasa_cambio"),
    path("api/integraciones/aliado/", AliadoAPIView.as_view(), name="api_aliado"),
]
