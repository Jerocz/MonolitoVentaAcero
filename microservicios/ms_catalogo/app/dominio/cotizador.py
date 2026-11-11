"""Reglas de negocio de la cotizacion (migradas desde CotizacionBuilder._validar).

Funciones puras: reciben los productos y los items ya parseados, devuelven
las lineas con precio o levantan `ReglaNegocioError`. No tocan la base de datos.
"""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from app.dominio.errores import ProductoNoEncontradoError, ReglaNegocioError, SolicitudInvalidaError
from app.dominio.precios import estrategia_para
from app.i18n import _


@dataclass
class ItemSolicitado:
    producto_id: int
    ancho_cm: Decimal
    largo_cm: Decimal
    cantidad: int


@dataclass
class LineaCotizada:
    producto: object
    ancho_cm: Decimal
    largo_cm: Decimal
    cantidad: int
    consumo_stock: Decimal
    subtotal: Decimal


def parsear_items(datos) -> list[ItemSolicitado]:
    if not isinstance(datos, list) or not datos:
        raise SolicitudInvalidaError(_("La cotización debe tener al menos un ítem."), "SIN_ITEMS")
    items = []
    for crudo in datos:
        try:
            items.append(ItemSolicitado(
                producto_id=int(crudo["producto_id"]),
                ancho_cm=Decimal(str(crudo["ancho_cm"])),
                largo_cm=Decimal(str(crudo["largo_cm"])),
                cantidad=int(crudo.get("cantidad", 1)),
            ))
        except (KeyError, TypeError, ValueError, InvalidOperation, AttributeError):
            raise SolicitudInvalidaError(
                _("Cada ítem necesita producto_id, ancho_cm, largo_cm y cantidad numéricos."),
                "ITEM_MAL_FORMADO")
    return items


def cotizar(items: list[ItemSolicitado], buscar_producto) -> list[LineaCotizada]:
    """Valida reglas y calcula precios. `buscar_producto(id)` devuelve el producto o None."""
    consumo_por_producto: dict[int, Decimal] = {}
    lineas = []
    for item in items:
        producto = buscar_producto(item.producto_id)
        if producto is None:
            raise ProductoNoEncontradoError(
                _("El producto {producto_id} no existe.", producto_id=item.producto_id))
        estrategia = estrategia_para(producto.tipo)

        if item.ancho_cm <= 0 or item.largo_cm <= 0 or item.cantidad <= 0:
            raise ReglaNegocioError(_("Medidas y cantidad deben ser positivas."), "MEDIDAS_INVALIDAS")
        if estrategia.es_a_medida and item.ancho_cm < estrategia.ANCHO_MINIMO_CM:
            raise ReglaNegocioError(
                _("'{nombre}': el ancho mínimo es {minimo} cm.",
                  nombre=producto.nombre, minimo=estrategia.ANCHO_MINIMO_CM),
                "ANCHO_MINIMO")

        consumo = estrategia.consumo_stock(item.ancho_cm, item.largo_cm, item.cantidad)
        acumulado = consumo_por_producto.get(producto.id, Decimal("0")) + consumo
        if Decimal(producto.stock_m2) < acumulado:
            raise ReglaNegocioError(
                _("'{nombre}': stock insuficiente (pide {pedido}, hay {disponible}).",
                  nombre=producto.nombre, pedido=f"{acumulado:.2f}",
                  disponible=f"{Decimal(producto.stock_m2):.2f}"),
                "STOCK_INSUFICIENTE")
        consumo_por_producto[producto.id] = acumulado

        subtotal = estrategia.calcular(producto.precio_base_m2, item.ancho_cm, item.largo_cm, item.cantidad)
        lineas.append(LineaCotizada(producto, item.ancho_cm, item.largo_cm, item.cantidad, consumo, subtotal))
    return lineas
