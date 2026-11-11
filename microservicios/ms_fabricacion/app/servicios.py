"""Casos de uso de las ordenes de fabricacion. Las rutas solo traducen HTTP."""
from decimal import Decimal

from sqlalchemy import select

from app.dominio.errores import ErrorFabricacion
from app.dominio.etapas import EtapaFinalError, etapa_inicial, fecha_estimada, siguiente_etapa
from app.i18n import _
from app.modelos import EventoOrden, Orden


class ServicioOrdenes:
    def __init__(self, sesion):
        self.s = sesion

    def crear(self, cotizacion_ref: str, cliente: str, total: Decimal) -> tuple[Orden, bool]:
        """Abre una orden para una cotizacion aprobada. Idempotente por cotizacion_ref
        (permite reintentos seguros desde la cola de tareas). Devuelve (orden, es_nueva)."""
        existente = self.s.scalar(select(Orden).where(Orden.cotizacion_ref == cotizacion_ref))
        if existente:
            return existente, False
        orden = Orden(cotizacion_ref=cotizacion_ref, cliente=cliente, total=total,
                      estado=etapa_inicial(), fecha_estimada_entrega=fecha_estimada())
        orden.eventos.append(EventoOrden(estado=orden.estado))
        self.s.add(orden)
        self.s.flush()
        return orden, True

    def listar(self, limite: int) -> list[Orden]:
        return list(self.s.scalars(select(Orden).order_by(Orden.id.desc()).limit(limite)))

    def obtener(self, orden_id: int, bloquear: bool = False) -> Orden:
        orden = self.s.get(Orden, orden_id, with_for_update=bloquear)
        if orden is None:
            raise ErrorFabricacion(404, "ORDEN_NO_EXISTE", _("La orden {id} no existe.", id=orden_id))
        return orden

    def avanzar(self, orden_id: int) -> Orden:
        orden = self.obtener(orden_id, bloquear=True)
        try:
            orden.estado = siguiente_etapa(orden.estado)
        except EtapaFinalError:
            raise ErrorFabricacion(409, "ORDEN_ENTREGADA", _("La orden {id} ya fue entregada.", id=orden_id))
        orden.eventos.append(EventoOrden(estado=orden.estado))
        self.s.flush()
        return orden
