"""Fachada sobre ms-fabricacion + ms-pagos para las ordenes de fabricacion."""
from django.utils.translation import gettext as _

from ventas.domain.dtos import EstadoPagoDTO, OrdenDTO
from ventas.domain.excepciones import (
    PagoRechazadoError,
    RecursoNoEncontradoError,
    ServicioNoDisponibleError,
)
from ventas.domain.puertos import ColaTareasPort, FabricacionPort, PagosPort
from ventas.domain.reglas import id_desde_referencia
from ventas.infra.contenedor import Contenedor
from ventas.models import Cotizacion


class OrdenService:
    """Fachada sobre ms-fabricacion + ms-pagos para las ordenes."""

    def __init__(self, fabricacion: FabricacionPort | None = None, pagos: PagosPort | None = None,
                 cola: ColaTareasPort | None = None):
        self.fabricacion = fabricacion or Contenedor.fabricacion()
        self.pagos = pagos or Contenedor.pagos()
        self.cola = cola or Contenedor.cola_tareas()

    def listar_con_pagos(self, limite=8) -> tuple[list[dict], bool]:
        """Ordenes con su estado de pago. Si ms-pagos esta caido, devuelve las
        ordenes igual (degradacion) e indica que el estado de pago es desconocido."""
        ordenes = self.fabricacion.listar_ordenes(limite)
        try:
            estados = self.pagos.estado([o.cotizacion_ref for o in ordenes])
            pagos_ok = True
        except ServicioNoDisponibleError:
            estados, pagos_ok = {}, False
        filas = [{"o": o, "saldo_pagado": estados.get(o.cotizacion_ref, EstadoPagoDTO()).saldo_pagado}
                 for o in ordenes]
        return filas, pagos_ok

    def avanzar_etapa(self, orden_id) -> OrdenDTO:
        orden = self.fabricacion.avanzar(orden_id)
        self.cola.notificar_cambio_etapa(orden.cotizacion_ref, orden.estado_display)
        return orden

    def pagar_saldo(self, orden_id) -> OrdenDTO:
        orden = self.fabricacion.obtener(orden_id)
        cotizacion = Cotizacion.objects.select_related("cliente").filter(
            pk=id_desde_referencia(orden.cotizacion_ref)).first()
        if cotizacion is None:
            raise RecursoNoEncontradoError(_("La cotización de la orden no existe."))
        cobro = self.pagos.cobrar_saldo(orden.cotizacion_ref, cotizacion.total, cotizacion.cliente.email)
        if not cobro.aprobado:
            raise PagoRechazadoError(_("La pasarela rechazó el saldo."))
        return orden
