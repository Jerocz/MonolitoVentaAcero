"""Adaptador HTTP de ms-fabricacion (implementa FabricacionPort)."""
from datetime import date
from decimal import Decimal

from django.utils.translation import gettext as _

from ventas.domain.dtos import OrdenDTO
from ventas.domain.excepciones import OperacionNoPermitidaError, RecursoNoEncontradoError
from ventas.domain.puertos import FabricacionPort
from ventas.infra.http import ClienteHttp
from ventas.infra.microservicios.base import respuesta_inesperada as _respuesta_inesperada


class FabricacionHttpAdapter(FabricacionPort):
    NOMBRE = "ms-fabricacion"

    def __init__(self, url_base: str):
        self.http = ClienteHttp(self.NOMBRE, url_base)

    @staticmethod
    def _orden(d: dict) -> OrdenDTO:
        return OrdenDTO(
            id=d["id"], cotizacion_ref=d["cotizacion_ref"], cliente=d["cliente"],
            total=Decimal(d["total"]), estado=d["estado"], estado_display=d["estado_display"],
            indice_etapa=d["indice_etapa"], progreso=d["progreso"],
            fecha_estimada_entrega=date.fromisoformat(d["fecha_estimada_entrega"]))

    def crear_orden(self, referencia, cliente, total):
        r = self.http.post("/api/fabricacion/ordenes",
                           json={"cotizacion_ref": referencia, "cliente": cliente, "total": str(total)})
        if r.status not in (200, 201):
            raise _respuesta_inesperada(self.NOMBRE, r)
        return self._orden(r.datos)

    def listar_ordenes(self, limite=8):
        r = self.http.get("/api/fabricacion/ordenes", limit=limite)
        if r.status != 200:
            raise _respuesta_inesperada(self.NOMBRE, r)
        return [self._orden(d) for d in r.datos]

    def obtener(self, orden_id):
        r = self.http.get(f"/api/fabricacion/ordenes/{int(orden_id)}")
        if r.status == 404:
            raise RecursoNoEncontradoError(_("La orden no existe."))
        if r.status != 200:
            raise _respuesta_inesperada(self.NOMBRE, r)
        return self._orden(r.datos)

    def avanzar(self, orden_id):
        r = self.http.post(f"/api/fabricacion/ordenes/{int(orden_id)}/avanzar")
        if r.status == 404:
            raise RecursoNoEncontradoError(_("La orden no existe."))
        if r.status == 409:
            raise OperacionNoPermitidaError(r.mensaje_error)
        if r.status != 200:
            raise _respuesta_inesperada(self.NOMBRE, r)
        return self._orden(r.datos)

    def etapas(self):
        r = self.http.get("/api/fabricacion/etapas")
        if r.status != 200:
            raise _respuesta_inesperada(self.NOMBRE, r)
        return [e["estado"] for e in r.datos]
