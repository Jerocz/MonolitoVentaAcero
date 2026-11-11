"""Acciones sobre las ordenes de fabricacion (avanzar etapa y pagar saldo)."""
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views import View

from ventas.domain.excepciones import (
    OperacionNoPermitidaError,
    PagoRechazadoError,
    RecursoNoEncontradoError,
    ServicioNoDisponibleError,
)
from ventas.services import OrdenService
from ventas.views.comunes import aviso_servicio


class _AccionOrdenView(View):
    def post(self, request, orden_id):
        try:
            self.ejecutar(request, orden_id)
        except (RecursoNoEncontradoError, OperacionNoPermitidaError, PagoRechazadoError) as e:
            messages.error(request, str(e))
        except ServicioNoDisponibleError:
            messages.error(request, aviso_servicio(_("El servicio requerido")))
        return redirect(reverse("cotizacion_form") + "#ordenes")


class AvanzarEtapaWebView(_AccionOrdenView):
    def ejecutar(self, request, orden_id):
        orden = OrdenService().avanzar_etapa(orden_id)
        messages.success(request, _("La orden #%(id)s pasó a la etapa: %(etapa)s.")
                         % {"id": orden.id, "etapa": orden.estado_display})


class PagarSaldoWebView(_AccionOrdenView):
    def ejecutar(self, request, orden_id):
        orden = OrdenService().pagar_saldo(orden_id)
        messages.success(request, _("Saldo de la orden #%(id)s pagado.") % {"id": orden.id})
