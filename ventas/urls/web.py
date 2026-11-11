"""Rutas de las paginas HTML."""
from django.urls import path

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
    path("", CotizacionFormView.as_view(), name="cotizacion_form"),
    path("ordenes/<int:orden_id>/avanzar/", AvanzarEtapaWebView.as_view(), name="avanzar_etapa"),
    path("ordenes/<int:orden_id>/saldo/", PagarSaldoWebView.as_view(), name="pagar_saldo"),
    path("integraciones/", IntegracionesView.as_view(), name="integraciones"),
    path("procesos/", ProcesosView.as_view(), name="procesos"),
    path("salud/", salud, name="salud"),
    path("salud/vivo/", salud_viva, name="salud_viva"),
]
