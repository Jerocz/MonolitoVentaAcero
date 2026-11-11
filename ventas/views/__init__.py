"""Vistas HTML. Solo traducen HTTP <-> servicios; la logica de negocio vive en
los servicios del monolito y en los microservicios.

    comunes.py        avisos de servicio caido y tasa de cambio
    cotizacion.py     pagina principal y formulario de cotizacion
    ordenes.py        avanzar etapa y pagar saldo
    integraciones.py  servicio propio, servicio aliado y API de terceros
    procesos.py       reportes y notificaciones (Celery)
    salud.py          healthchecks
"""
from ventas.views.cotizacion import CotizacionFormView
from ventas.views.integraciones import IntegracionesView
from ventas.views.ordenes import AvanzarEtapaWebView, PagarSaldoWebView
from ventas.views.procesos import ProcesosView
from ventas.views.salud import salud, salud_viva

__all__ = ["AvanzarEtapaWebView", "CotizacionFormView", "IntegracionesView", "PagarSaldoWebView",
           "ProcesosView", "salud", "salud_viva"]
