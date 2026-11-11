"""Procesos en segundo plano: reportes y notificaciones generados por Celery."""
from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _
from django.views import View

from ventas.infra.contenedor import Contenedor
from ventas.models import Notificacion, ReporteVentas


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
