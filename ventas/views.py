"""Capa de Interfaz: la vista solo captura datos y delega en el CotizacionService."""
import json
import os

from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from ventas.domain.excepciones import PagoRechazadoError, PedidoInvalidoError
from ventas.models import Cliente, Cotizacion, OrdenFabricacion, Producto
from ventas.services import CotizacionService


class CotizacionFormView(View):
    def _contexto(self):
        env = os.getenv("ENV_TYPE", "MOCK").upper()
        return {
            "clientes": Cliente.objects.all(),
            "productos": Producto.objects.all(),
            "cotizaciones": Cotizacion.objects.select_related("cliente").order_by("-id")[:8],
            "ordenes": OrdenFabricacion.objects.select_related("cotizacion__cliente").order_by("-id")[:8],
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
        except (PedidoInvalidoError, PagoRechazadoError) as e:
            contexto["error"] = str(e)
        contexto.update(
            cotizaciones=Cotizacion.objects.select_related("cliente").order_by("-id")[:8],
            ordenes=OrdenFabricacion.objects.select_related("cotizacion__cliente").order_by("-id")[:8])
        return render(request, "ventas/venta_form.html", contexto)


class AvanzarEtapaView(View):
    def post(self, request, orden_id):
        OrdenFabricacion.objects.get(pk=orden_id).avanzar_etapa()
        return redirect("cotizacion_form")


class PagarSaldoView(View):
    def post(self, request, orden_id):
        try:
            CotizacionService().pagar_saldo(orden_id)
        except PagoRechazadoError:
            pass
        return redirect("cotizacion_form")


@method_decorator(csrf_exempt, name="dispatch")
class ProcesarCotizacionView(View):
    """Endpoint JSON. La logica de negocio vive en el servicio, no aqui."""
    def post(self, request):
        datos = json.loads(request.body)
        try:
            cotizacion = CotizacionService().crear_cotizacion(
                cliente_id=datos["cliente_id"], items=datos["items"])
        except PedidoInvalidoError as e:
            return JsonResponse({"error": str(e)}, status=400)
        except PagoRechazadoError as e:
            return JsonResponse({"error": str(e)}, status=402)
        return JsonResponse({"cotizacion_id": cotizacion.pk, "estado": cotizacion.estado,
                            "total": str(cotizacion.total)}, status=201)
