from django.urls import path

from ventas.views import (
    AvanzarEtapaView,
    CotizacionFormView,
    PagarSaldoView,
    ProcesarCotizacionView,
)

urlpatterns = [
    path("", CotizacionFormView.as_view(), name="cotizacion_form"),
    path("ordenes/<int:orden_id>/avanzar/", AvanzarEtapaView.as_view(), name="avanzar_etapa"),
    path("ordenes/<int:orden_id>/saldo/", PagarSaldoView.as_view(), name="pagar_saldo"),
    path("cotizaciones/procesar/", ProcesarCotizacionView.as_view(), name="procesar_cotizacion"),
]
