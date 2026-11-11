"""Adaptador HTTP de ms-catalogo (implementa CatalogoPort)."""
from decimal import Decimal

from ventas.domain.dtos import LineaReservadaDTO, ProductoDTO, ReservaDTO
from ventas.domain.excepciones import PedidoInvalidoError, RecursoNoEncontradoError
from ventas.domain.puertos import CatalogoPort
from ventas.infra.http import ClienteHttp
from ventas.infra.microservicios.base import respuesta_inesperada as _respuesta_inesperada


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
