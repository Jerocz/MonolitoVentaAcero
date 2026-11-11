"""Utilidades compartidas por las vistas HTML."""
from django.utils.translation import gettext as _

from ventas.domain.excepciones import ServicioNoDisponibleError
from ventas.infra.contenedor import Contenedor


def aviso_servicio(servicio_legible: str) -> str:
    return _("%(servicio)s no está disponible en este momento. Mostramos lo que se pudo cargar; "
             "intenta de nuevo en unos minutos.") % {"servicio": servicio_legible}


def tasa_cop_usd():
    try:
        return Contenedor.tasa_cambio().obtener("COP", "USD")
    except ServicioNoDisponibleError:
        return None
