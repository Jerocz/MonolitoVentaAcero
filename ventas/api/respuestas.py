"""Respuestas comunes de la API."""
from dataclasses import asdict

from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.response import Response

from ventas.domain.excepciones import ServicioNoDisponibleError


def no_disponible(e: ServicioNoDisponibleError):
    return Response({"error": _("Servicio no disponible: %(servicio)s") % {"servicio": e.servicio}},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE)


def orden_json(orden):
    datos = asdict(orden)
    datos["total"] = str(orden.total)
    datos["fecha_estimada_entrega"] = orden.fecha_estimada_entrega.isoformat()
    return datos
