"""Vistas HTML. Solo traducen HTTP <-> servicios; toda la logica de negocio
vive en los servicios del monolito y en los microservicios.

Usabilidad: patron Post/Redirect/Get (recargar la pagina nunca cobra dos
veces), mensajes de exito/error, errores por campo y degradacion controlada
cuando un microservicio no responde (la pagina sigue funcionando).
"""
import logging

from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views import View

from ventas.domain.excepciones import (
    OperacionNoPermitidaError,
    PagoRechazadoError,
    PedidoInvalidoError,
    RecursoNoEncontradoError,
    ServicioNoDisponibleError,
)
from ventas.forms import CotizacionForm
from ventas.infra.contenedor import Contenedor
from ventas.infra.http import ClienteHttp, estado_circuitos
from ventas.models import Cliente, Cotizacion, Notificacion, ReporteVentas
from ventas.services import CotizacionService, OrdenService

log = logging.getLogger(__name__)
ETAPAS_POR_DEFECTO = 6


def _aviso_servicio(servicio_legible: str) -> str:
    return _("%(servicio)s no está disponible en este momento. Mostramos lo que se pudo cargar; "
             "intenta de nuevo en unos minutos.") % {"servicio": servicio_legible}


def _tasa():
    try:
        return Contenedor.tasa_cambio().obtener("COP", "USD")
    except ServicioNoDisponibleError:
        return None


class CotizacionFormView(View):
    plantilla = "ventas/venta_form.html"

    def _productos(self, avisos):
        try:
            return Contenedor.catalogo().listar_productos()
        except ServicioNoDisponibleError:
            avisos.append(_aviso_servicio(_("El catálogo")))
            return []

    def _contexto(self, request, form=None, productos=None, avisos=None):
        avisos = [] if avisos is None else avisos
        productos = self._productos(avisos) if productos is None else productos
        clientes = list(Cliente.objects.order_by("nombre"))
        tasa = _tasa()

        ordenes, pagos_ok, total_etapas = [], True, ETAPAS_POR_DEFECTO
        try:
            fabricacion = Contenedor.fabricacion()
            ordenes, pagos_ok = OrdenService(fabricacion=fabricacion).listar_con_pagos(8)
            total_etapas = len(fabricacion.etapas())
        except ServicioNoDisponibleError:
            avisos.append(_aviso_servicio(_("El seguimiento de fabricación")))
        if not pagos_ok:
            avisos.append(_aviso_servicio(_("El servicio de pagos")))

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


class _AccionOrdenView(View):
    def post(self, request, orden_id):
        try:
            self.ejecutar(request, orden_id)
        except (RecursoNoEncontradoError, OperacionNoPermitidaError, PagoRechazadoError) as e:
            messages.error(request, str(e))
        except ServicioNoDisponibleError:
            messages.error(request, _aviso_servicio(_("El servicio requerido")))
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


class IntegracionesView(View):
    """Servicio a proveer, servicio del aliado consumido y API de terceros."""

    def get(self, request):
        return render(request, "ventas/integraciones.html", {
            "tasa": _tasa(),
            "aliado": Contenedor.aliado().consultar(),
            "url_publica": request.build_absolute_uri("/api/catalogo/publico/v1/productos"),
        })


class ProcesosView(View):
    """Procesos en segundo plano: reportes y notificaciones generados por Celery."""

    def get(self, request):
        return render(request, "ventas/procesos.html", {
            "reportes": ReporteVentas.objects.all()[:10],
            "notificaciones": Notificacion.objects.all()[:10],
        })

    def post(self, request):
        reporte = ReporteVentas.objects.create()
        Contenedor.cola_tareas().generar_reporte(reporte.id)
        messages.success(request, _("Reporte #%(id)s en cola. Se genera en segundo plano; recarga en unos segundos.")
                         % {"id": reporte.id})
        return redirect("procesos")


def salud_viva(request):
    """Liveness para el healthcheck de Docker (no depende de otros servicios)."""
    return JsonResponse({"servicio": "monolito-django", "estado": "ok"})


def salud(request):
    """Estado del ecosistema completo (util en la sustentacion)."""
    componentes = {}
    try:
        connection.ensure_connection()
        componentes["base_de_datos"] = "ok"
    except Exception:
        componentes["base_de_datos"] = "caido"
    try:
        cache.set("salud", "ok", 5)
        componentes["cache"] = "ok" if cache.get("salud") == "ok" else "caido"
    except Exception:
        componentes["cache"] = "caido"
    for nombre, url in settings.MICROSERVICIOS.items():
        ruta = f"/api/{nombre.lower()}/health"
        try:
            r = ClienteHttp(f"salud-{nombre.lower()}", url, timeout=2).get(ruta)
            componentes[f"ms_{nombre.lower()}"] = "ok" if r.status == 200 else f"HTTP {r.status}"
        except ServicioNoDisponibleError:
            componentes[f"ms_{nombre.lower()}"] = "caido"
    try:
        from monolito_venta_acero.celery import app
        respuesta = app.control.ping(timeout=1.0)
        componentes["celery_worker"] = "ok" if respuesta else "sin workers"
    except Exception:
        componentes["celery_worker"] = "caido"
    estado = "ok" if all(v == "ok" for v in componentes.values()) else "degradado"
    return JsonResponse({"estado": estado, "componentes": componentes, "circuitos": estado_circuitos()})
