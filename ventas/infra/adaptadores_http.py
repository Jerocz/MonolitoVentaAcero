"""Adaptadores HTTP hacia los microservicios Flask (implementan los puertos).

Cada adaptador traduce el contrato JSON de su microservicio a los DTOs del
dominio y los codigos HTTP a excepciones de dominio.
"""
from datetime import date
from decimal import Decimal

from django.utils.translation import gettext as _

from ventas.domain.excepciones import (
    OperacionNoPermitidaError,
    PedidoInvalidoError,
    RecursoNoEncontradoError,
    ServicioNoDisponibleError,
)
from ventas.domain.puertos import (
    CatalogoPort,
    CobroDTO,
    EstadoPagoDTO,
    FabricacionPort,
    LineaReservadaDTO,
    OrdenDTO,
    PagosPort,
    ProductoDTO,
    ReservaDTO,
)
from ventas.infra.http import ClienteHttp, RespuestaHttp


def _respuesta_inesperada(nombre: str, r: RespuestaHttp):
    return ServicioNoDisponibleError(nombre, f"HTTP {r.status}")


# ============================================================== Catalogo
class CatalogoHttpAdapter(CatalogoPort):
    NOMBRE = "ms-catalogo"

    def __init__(self, url_base: str):
        self.http = ClienteHttp(self.NOMBRE, url_base)

    @staticmethod
    def _producto(d: dict) -> ProductoDTO:
        return ProductoDTO(
            id=d["id"], nombre=d["nombre"], tipo=d["tipo"], tipo_display=d["tipo_display"],
            calibre_acero=d["calibre_acero"], precio_base_m2=Decimal(d["precio_base_m2"]),
            stock_m2=Decimal(d["stock_m2"]), es_a_medida=d["es_a_medida"], unidad=d["unidad"],
            ancho_minimo_cm=Decimal(d["ancho_minimo_cm"]) if d.get("ancho_minimo_cm") else None)

    def listar_productos(self):
        r = self.http.get("/api/catalogo/productos")
        if r.status != 200:
            raise _respuesta_inesperada(self.NOMBRE, r)
        return [self._producto(d) for d in r.datos]

    def reservar(self, referencia, items):
        cuerpo = {"referencia": referencia, "items": [
            {"producto_id": int(i["producto_id"]), "ancho_cm": str(i["ancho_cm"]),
             "largo_cm": str(i["largo_cm"]), "cantidad": int(i.get("cantidad", 1))} for i in items]}
        r = self.http.post("/api/catalogo/reservas", json=cuerpo)
        if r.status == 404:
            raise RecursoNoEncontradoError(r.mensaje_error)
        if r.status in (400, 409):
            raise PedidoInvalidoError(r.mensaje_error)
        if r.status not in (200, 201):
            raise _respuesta_inesperada(self.NOMBRE, r)
        d = r.datos
        return ReservaDTO(
            referencia=d["referencia"], total=Decimal(d["total"]),
            lineas=[LineaReservadaDTO(
                producto_id=l["producto_id"], producto_nombre=l["producto_nombre"],
                producto_tipo=l["producto_tipo"], ancho_cm=Decimal(l["ancho_cm"]),
                largo_cm=Decimal(l["largo_cm"]), cantidad=l["cantidad"],
                subtotal=Decimal(l["subtotal"])) for l in d["lineas"]])

    def liberar(self, referencia):
        r = self.http.post(f"/api/catalogo/reservas/{referencia}/liberar")
        if r.status not in (200, 404):
            raise _respuesta_inesperada(self.NOMBRE, r)


# ================================================================ Pagos
class PagosHttpAdapter(PagosPort):
    NOMBRE = "ms-pagos"

    def __init__(self, url_base: str):
        self.http = ClienteHttp(self.NOMBRE, url_base)

    def _cobrar(self, ruta, referencia, total, email) -> CobroDTO:
        r = self.http.post(ruta, json={"concepto_ref": referencia, "total": str(total), "email": email})
        if r.status in (200, 201, 402):  # 402 = rechazado por la pasarela (respuesta valida)
            return CobroDTO(aprobado=bool(r.datos["aprobado"]), monto=Decimal(r.datos["monto"]),
                            referencia=r.datos["referencia"])
        if r.status in (400, 409):
            raise OperacionNoPermitidaError(r.mensaje_error)
        raise _respuesta_inesperada(self.NOMBRE, r)

    def cobrar_anticipo(self, referencia, total, email):
        return self._cobrar("/api/pagos/anticipos", referencia, total, email)

    def cobrar_saldo(self, referencia, total, email):
        return self._cobrar("/api/pagos/saldos", referencia, total, email)

    def estado(self, referencias):
        if not referencias:
            return {}
        r = self.http.get("/api/pagos/estado", refs=",".join(referencias))
        if r.status != 200:
            raise _respuesta_inesperada(self.NOMBRE, r)
        return {ref: EstadoPagoDTO(anticipo_pagado=v["anticipo_pagado"], saldo_pagado=v["saldo_pagado"])
                for ref, v in r.datos.items()}


# ========================================================== Fabricacion
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
