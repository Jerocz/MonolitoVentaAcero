"""Servicio que proveemos, servicio del aliado y API de terceros."""
from django.shortcuts import render
from django.views import View

from ventas.infra.contenedor import Contenedor
from ventas.views.comunes import tasa_cop_usd


class IntegracionesView(View):
    """Servicio a proveer, servicio del aliado consumido y API de terceros."""

    def get(self, request):
        return render(request, "ventas/integraciones.html", {
            "tasa": tasa_cop_usd(),
            "aliado": Contenedor.aliado().consultar(),
            "url_publica": request.build_absolute_uri("/api/catalogo/publico/v1/productos"),
        })
