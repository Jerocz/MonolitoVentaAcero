"""Reserva de stock (paso 2 de la saga de cotizacion) y su compensacion."""
from decimal import Decimal

from flask import Blueprint, jsonify
from sqlalchemy import select

from app.dominio.cotizador import cotizar, parsear_items
from app.dominio.errores import ReservaNoEncontradaError, SolicitudInvalidaError
from app.i18n import _
from app.modelos import LineaReserva, Producto, Reserva
from app.rutas.comun import PREFIJO, db, json_entrada
from app.serializadores import reserva_json

bp = Blueprint("reservas", __name__, url_prefix=PREFIJO)


@bp.post("/reservas")
def reservar():
    """Valida, calcula precios y descuenta stock en una sola transaccion.
    Idempotente por `referencia`: repetir la llamada devuelve la misma reserva."""
    datos = json_entrada()
    referencia = str(datos.get("referencia") or "").strip()
    if not referencia:
        raise SolicitudInvalidaError(_("Falta la referencia de la cotización."), "SIN_REFERENCIA")
    items = parsear_items(datos.get("items"))

    with db().sesion() as s:
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
    with db().sesion() as s:
        reserva = s.scalar(select(Reserva).where(Reserva.referencia == referencia))
        if reserva is None:
            raise ReservaNoEncontradaError(_("La reserva {referencia} no existe.", referencia=referencia))
        if reserva.estado == Reserva.ACTIVA:
            for linea in reserva.lineas:
                producto = s.get(Producto, linea.producto_id, with_for_update=True)
                producto.stock_m2 = Decimal(producto.stock_m2) + Decimal(linea.consumo_stock)
            reserva.estado = Reserva.LIBERADA
        return jsonify(reserva_json(reserva))
