"""Conversion de modelos y resultados del dominio a JSON (contrato de la API)."""
from decimal import Decimal

from app.dominio.precios import estrategia_para
from app.i18n import _
from app.modelos import Producto, Reserva


def nombre_tipo(tipo: str) -> str:
    nombres = {
        "LAMINA": _("Lámina a la medida"),
        "MESON": _("Mesón"),
        "CAMPANA": _("Campana extractora"),
        "FREIDORA": _("Freidora (estándar)"),
    }
    return nombres.get(tipo, tipo)


def dinero(valor) -> str:
    return str(Decimal(valor).quantize(Decimal("0.01")))


def producto_json(p: Producto) -> dict:
    estrategia = estrategia_para(p.tipo)
    return {
        "id": p.id,
        "nombre": p.nombre,
        "tipo": p.tipo,
        "tipo_display": nombre_tipo(p.tipo),
        "calibre_acero": p.calibre_acero,
        "precio_base_m2": dinero(p.precio_base_m2),
        "stock_m2": dinero(p.stock_m2),
        "es_a_medida": estrategia.es_a_medida,
        "unidad": estrategia.unidad,
        "ancho_minimo_cm": str(estrategia.ANCHO_MINIMO_CM) if estrategia.es_a_medida else None,
    }


def producto_publico_json(p: Producto) -> dict:
    datos = {k: v for k, v in producto_json(p).items() if k != "ancho_minimo_cm"}
    datos["disponible"] = Decimal(p.stock_m2) > 0
    return datos


def _linea(producto_id, nombre, tipo, ancho, largo, cantidad, subtotal) -> dict:
    return {
        "producto_id": producto_id,
        "producto_nombre": nombre,
        "producto_tipo": tipo,
        "producto_tipo_display": nombre_tipo(tipo),
        "ancho_cm": str(Decimal(ancho).quantize(Decimal("0.1"))),
        "largo_cm": str(Decimal(largo).quantize(Decimal("0.1"))),
        "cantidad": cantidad,
        "subtotal": dinero(subtotal),
    }


def linea_cotizada_json(l) -> dict:
    return _linea(l.producto.id, l.producto.nombre, l.producto.tipo,
                  l.ancho_cm, l.largo_cm, l.cantidad, l.subtotal)


def reserva_json(r: Reserva) -> dict:
    return {
        "referencia": r.referencia,
        "estado": r.estado,
        "total": dinero(r.total),
        "lineas": [_linea(l.producto_id, l.producto_nombre, l.producto_tipo,
                          l.ancho_cm, l.largo_cm, l.cantidad, l.subtotal) for l in r.lineas],
    }
