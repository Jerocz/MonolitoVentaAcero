"""API HTTP del microservicio de catalogo (JSON)."""
from datetime import datetime, timezone
from decimal import Decimal

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import select

from app.dominio.cotizador import (
    ErrorCatalogo,
    SolicitudInvalidaError,
    cotizar,
    parsear_items,
)
from app.dominio.precios import TIPOS, estrategia_para
from app.i18n import _, idioma_actual
from app.modelos import LineaReserva, Producto, Reserva

bp = Blueprint("catalogo", __name__, url_prefix="/api/catalogo")


def _db():
    return current_app.extensions["db"]


def nombre_tipo(tipo: str) -> str:
    nombres = {
        "LAMINA": _("Lámina a la medida"),
        "MESON": _("Mesón"),
        "CAMPANA": _("Campana extractora"),
        "FREIDORA": _("Freidora (estándar)"),
    }
    return nombres.get(tipo, tipo)


def producto_json(p: Producto) -> dict:
    estrategia = estrategia_para(p.tipo)
    return {
        "id": p.id,
        "nombre": p.nombre,
        "tipo": p.tipo,
        "tipo_display": nombre_tipo(p.tipo),
        "calibre_acero": p.calibre_acero,
        "precio_base_m2": str(Decimal(p.precio_base_m2).quantize(Decimal("0.01"))),
        "stock_m2": str(Decimal(p.stock_m2).quantize(Decimal("0.01"))),
        "es_a_medida": estrategia.es_a_medida,
        "unidad": estrategia.unidad,
        "ancho_minimo_cm": str(estrategia.ANCHO_MINIMO_CM) if estrategia.es_a_medida else None,
    }


def _linea(producto_id, nombre, tipo, ancho, largo, cantidad, subtotal) -> dict:
    return {
        "producto_id": producto_id,
        "producto_nombre": nombre,
        "producto_tipo": tipo,
        "producto_tipo_display": nombre_tipo(tipo),
        "ancho_cm": str(Decimal(ancho).quantize(Decimal("0.1"))),
        "largo_cm": str(Decimal(largo).quantize(Decimal("0.1"))),
        "cantidad": cantidad,
        "subtotal": str(Decimal(subtotal).quantize(Decimal("0.01"))),
    }


def linea_cotizada_json(l) -> dict:
    return _linea(l.producto.id, l.producto.nombre, l.producto.tipo,
                  l.ancho_cm, l.largo_cm, l.cantidad, l.subtotal)


def reserva_json(r: Reserva) -> dict:
    return {
        "referencia": r.referencia,
        "estado": r.estado,
        "total": str(Decimal(r.total).quantize(Decimal("0.01"))),
        "lineas": [_linea(l.producto_id, l.producto_nombre, l.producto_tipo,
                          l.ancho_cm, l.largo_cm, l.cantidad, l.subtotal) for l in r.lineas],
    }


@bp.errorhandler(ErrorCatalogo)
def _error_catalogo(error: ErrorCatalogo):
    return jsonify({"error": error.mensaje, "codigo": error.codigo}), error.status


def _json_entrada() -> dict:
    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        raise SolicitudInvalidaError(_("El cuerpo debe ser un objeto JSON."), "JSON_INVALIDO")
    return datos


# ---------------------------------------------------------------- salud
@bp.get("/health")
def salud():
    with _db().sesion() as s:
        s.execute(select(1))
    return jsonify({"servicio": "ms-catalogo", "estado": "ok"})


# ---------------------------------------------------------------- productos
@bp.get("/productos")
def listar_productos():
    with _db().sesion() as s:
        productos = s.scalars(select(Producto).order_by(Producto.id)).all()
        return jsonify([producto_json(p) for p in productos])


@bp.get("/productos/<int:producto_id>")
def obtener_producto(producto_id):
    with _db().sesion() as s:
        p = s.get(Producto, producto_id)
        if p is None:
            return jsonify({"error": _("El producto {producto_id} no existe.", producto_id=producto_id),
                            "codigo": "PRODUCTO_NO_EXISTE"}), 404
        return jsonify(producto_json(p))


@bp.post("/productos")
def crear_producto():
    datos = _json_entrada()
    try:
        tipo = str(datos["tipo"]).upper()
        precio = Decimal(str(datos["precio_base_m2"]))
        stock = Decimal(str(datos["stock_m2"]))
        calibre = int(datos["calibre_acero"])
        nombre = str(datos["nombre"]).strip()
    except Exception:
        raise SolicitudInvalidaError(_("Faltan campos o tienen un formato inválido."), "PRODUCTO_INVALIDO")
    if tipo not in TIPOS or calibre not in (304, 430) or precio <= 0 or stock < 0 or not nombre:
        raise SolicitudInvalidaError(_("Faltan campos o tienen un formato inválido."), "PRODUCTO_INVALIDO")
    with _db().sesion() as s:
        p = Producto(nombre=nombre, tipo=tipo, calibre_acero=calibre, precio_base_m2=precio, stock_m2=stock)
        s.add(p)
        s.flush()
        return jsonify(producto_json(p)), 201


# ---------------------------------------------------------------- cotizar
@bp.post("/cotizaciones/simular")
def simular():
    """Calcula precios y valida reglas SIN apartar stock."""
    items = parsear_items(_json_entrada().get("items"))
    with _db().sesion() as s:
        lineas = cotizar(items, lambda pid: s.get(Producto, pid))
        total = sum((l.subtotal for l in lineas), Decimal("0"))
        return jsonify({"total": str(total), "lineas": [linea_cotizada_json(l) for l in lineas]})


@bp.post("/reservas")
def reservar():
    """Valida, calcula precios y descuenta stock en una sola transaccion.
    Idempotente por `referencia`: repetir la llamada devuelve la misma reserva."""
    datos = _json_entrada()
    referencia = str(datos.get("referencia") or "").strip()
    if not referencia:
        raise SolicitudInvalidaError(_("Falta la referencia de la cotización."), "SIN_REFERENCIA")
    items = parsear_items(datos.get("items"))

    with _db().sesion() as s:
        existente = s.scalar(select(Reserva).where(Reserva.referencia == referencia))
        if existente is not None and existente.estado == Reserva.ACTIVA:
            return jsonify(reserva_json(existente)), 200

        ids = sorted({i.producto_id for i in items})
        # Bloquea las filas de producto para que dos reservas simultaneas no vendan el mismo stock.
        bloqueados = {p.id: p for p in s.scalars(
            select(Producto).where(Producto.id.in_(ids)).with_for_update())}
        lineas = cotizar(items, bloqueados.get)

        total = sum((l.subtotal for l in lineas), Decimal("0"))
        if existente is None:
            reserva = Reserva(referencia=referencia, total=total)
            s.add(reserva)
        else:  # una reserva liberada se puede volver a activar
            reserva = existente
            reserva.estado, reserva.total = Reserva.ACTIVA, total
            reserva.lineas.clear()
        for l in lineas:
            l.producto.stock_m2 = Decimal(l.producto.stock_m2) - l.consumo_stock
            reserva.lineas.append(LineaReserva(
                producto_id=l.producto.id, producto_nombre=l.producto.nombre,
                producto_tipo=l.producto.tipo, ancho_cm=l.ancho_cm, largo_cm=l.largo_cm,
                cantidad=l.cantidad, consumo_stock=l.consumo_stock, subtotal=l.subtotal))
        s.flush()
        return jsonify(reserva_json(reserva)), 201


@bp.post("/reservas/<referencia>/liberar")
def liberar(referencia):
    """Transaccion compensatoria: devuelve el stock de una reserva (p. ej. pago rechazado)."""
    with _db().sesion() as s:
        reserva = s.scalar(select(Reserva).where(Reserva.referencia == referencia))
        if reserva is None:
            return jsonify({"error": _("La reserva {referencia} no existe.", referencia=referencia),
                            "codigo": "RESERVA_NO_EXISTE"}), 404
        if reserva.estado == Reserva.ACTIVA:
            for linea in reserva.lineas:
                producto = s.get(Producto, linea.producto_id, with_for_update=True)
                producto.stock_m2 = Decimal(producto.stock_m2) + Decimal(linea.consumo_stock)
            reserva.estado = Reserva.LIBERADA
        return jsonify(reserva_json(reserva))


# ---------------------------------------------------------------- servicio publico
@bp.get("/publico/v1/productos")
def publico_productos():
    """Servicio que PROVEEMOS al equipo aliado: catalogo vigente con precios y stock."""
    with _db().sesion() as s:
        productos = s.scalars(select(Producto).order_by(Producto.id)).all()
        return jsonify({
            "proveedor": "Integrales Torres B.",
            "descripcion": _("Catálogo de productos en acero inoxidable fabricados a la medida."),
            "moneda": "COP",
            "idioma": idioma_actual(),
            "generado_en": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "total_productos": len(productos),
            "productos": [
                {k: v for k, v in producto_json(p).items() if k != "ancho_minimo_cm"}
                | {"disponible": Decimal(p.stock_m2) > 0}
                for p in productos
            ],
        })
