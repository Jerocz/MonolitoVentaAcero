"""Vistas HTML (para la sustentacion). Solo delegan en los servicios;
los calculos de display se piden a los servicios, no a los modelos."""
import os

from django.shortcuts import redirect, render
from django.views import View

from ventas.domain.excepciones import PagoRechazadoError, PedidoInvalidoError
from ventas.domain.reglas import SECUENCIA_ETAPAS
from ventas.models import Cliente, Cotizacion, OrdenFabricacion, Producto
from ventas.services import CotizacionService, OrdenService


class CotizacionFormView(View):
    def _contexto(self):
        env = os.getenv("ENV_TYPE", "MOCK").upper()
        orden_srv = OrdenService()
        ordenes = OrdenFabricacion.objects.select_related("cotizacion__cliente").order_by("-id")[:8]
        return {
            "clientes": Cliente.objects.all(),
            "productos": Producto.objects.all(),
            "cotizaciones": Cotizacion.objects.select_related("cliente").order_by("-id")[:8],
            "ordenes": [{"o": o, "saldo_pagado": orden_srv.saldo_pagado(o)} for o in ordenes],
            "secuencia": SECUENCIA_ETAPAS,
            "env_type": env,
            "pasarela_nombre": "PasarelaReal" if env == "REAL" else "PasarelaMock",
        }

    def get(self, request):
        return render(request, "ventas/venta_form.html", self._contexto())

    def post(self, request):
        contexto = self._contexto()
        try:
            cotizacion = CotizacionService().crear_cotizacion(
                cliente_id=request.POST["cliente_id"],
                items=[{
                    "producto_id": request.POST["producto_id"],
                    "ancho_cm": request.POST["ancho_cm"],
                    "largo_cm": request.POST["largo_cm"],
                    "cantidad": request.POST.get("cantidad", 1),
                }])
            contexto["resultado"] = cotizacion
            contexto["resultado_anticipo"] = CotizacionService.calcular_anticipo(cotizacion.total)
        except (PedidoInvalidoError, PagoRechazadoError) as e:
            contexto["error"] = str(e)
        return render(request, "ventas/venta_form.html", contexto)


class AvanzarEtapaWebView(View):
    def post(self, request, orden_id):
        OrdenService().avanzar_etapa(orden_id)
        return redirect("cotizacion_form")


class PagarSaldoWebView(View):
    def post(self, request, orden_id):
        try:
            OrdenService().pagar_saldo(orden_id)
        except PagoRechazadoError:
            pass
        return redirect("cotizacion_form")
