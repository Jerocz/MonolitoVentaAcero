"""Pagina principal: catalogo, cotizador, ordenes y ultimas cotizaciones.

Usabilidad: patron Post/Redirect/Get (recargar la pagina nunca cobra dos
veces), errores por campo y degradacion controlada cuando un microservicio
no responde (la pagina sigue funcionando).
"""
import logging

from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views import View

from ventas.domain.excepciones import (
    PagoRechazadoError,
    PedidoInvalidoError,
    RecursoNoEncontradoError,
    ServicioNoDisponibleError,
)
from ventas.forms import CotizacionForm
from ventas.infra.contenedor import Contenedor
from ventas.models import Cliente, Cotizacion
from ventas.services import CotizacionService, OrdenService
from ventas.views.comunes import aviso_servicio, tasa_cop_usd

log = logging.getLogger(__name__)
ETAPAS_POR_DEFECTO = 6


class CotizacionFormView(View):
    plantilla = "ventas/venta_form.html"

    def _productos(self, avisos):
        try:
            return Contenedor.catalogo().listar_productos()
        except ServicioNoDisponibleError:
            avisos.append(aviso_servicio(_("El catálogo")))
            return []

    def _contexto(self, request, form=None, productos=None, avisos=None):
        avisos = [] if avisos is None else avisos
        productos = self._productos(avisos) if productos is None else productos
        clientes = list(Cliente.objects.order_by("nombre"))
        tasa = tasa_cop_usd()

        ordenes, pagos_ok, total_etapas = [], True, ETAPAS_POR_DEFECTO
        try:
            fabricacion = Contenedor.fabricacion()
            ordenes, pagos_ok = OrdenService(fabricacion=fabricacion).listar_con_pagos(8)
            total_etapas = len(fabricacion.etapas())
        except ServicioNoDisponibleError:
            avisos.append(aviso_servicio(_("El seguimiento de fabricación")))
        if not pagos_ok:
            avisos.append(aviso_servicio(_("El servicio de pagos")))

        resultado = None
        if request.GET.get("cotizacion", "").isdigit():
            resultado = Cotizacion.objects.select_related("cliente").filter(pk=request.GET["cotizacion"]).first()

        return {
            "form": form or CotizacionForm(clientes=clientes, productos=productos),
            "productos": [{"p": p, "precio_usd": tasa.convertir(p.precio_base_m2) if tasa else None}
                          for p in productos],
            "tasa": tasa,
            "cotizaciones": Cotizacion.objects.select_related("cliente").order_by("-id")[:8],
            "ordenes": ordenes,
            "pagos_ok": pagos_ok,
            "etapas": range(total_etapas),
            "avisos": avisos,
            "resultado": resultado,
        }

    def get(self, request):
        return render(request, self.plantilla, self._contexto(request))

    def post(self, request):
        avisos = []
        productos = self._productos(avisos)
        form = CotizacionForm(request.POST, clientes=Cliente.objects.order_by("nombre"), productos=productos)
        if not form.is_valid():
            return render(request, self.plantilla,
                          self._contexto(request, form=form, productos=productos, avisos=avisos), status=400)
        try:
            cotizacion = CotizacionService().crear_cotizacion(form.cleaned_data["cliente_id"], form.como_items())
        except (PedidoInvalidoError, PagoRechazadoError, RecursoNoEncontradoError) as e:
            form.add_error(None, str(e))
        except ServicioNoDisponibleError as e:
            log.warning("Cotizacion no completada: %s", e)
            form.add_error(None, _("No pudimos completar la cotización porque un servicio interno no "
                                   "responde. No se realizó ningún cobro; intenta de nuevo en unos minutos."))
        else:
            messages.success(request, _("Cotización %(ref)s aprobada. Te enviaremos la confirmación por correo.")
                             % {"ref": cotizacion.referencia})
            return redirect(f"{reverse('cotizacion_form')}?cotizacion={cotizacion.id}#cotizador")
        return render(request, self.plantilla,
                      self._contexto(request, form=form, productos=productos, avisos=avisos), status=409)
