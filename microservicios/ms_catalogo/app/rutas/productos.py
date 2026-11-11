from decimal import Decimal

from flask import Blueprint, jsonify
from sqlalchemy import select

from app.dominio.errores import ProductoNoEncontradoError, SolicitudInvalidaError
from app.dominio.precios import TIPOS
from app.i18n import _
from app.modelos import Producto
from app.rutas.comun import PREFIJO, db, json_entrada
from app.serializadores import producto_json

bp = Blueprint("productos", __name__, url_prefix=PREFIJO)


@bp.get("/productos")
def listar_productos():
    with db().sesion() as s:
        productos = s.scalars(select(Producto).order_by(Producto.id)).all()
        return jsonify([producto_json(p) for p in productos])


@bp.get("/productos/<int:producto_id>")
def obtener_producto(producto_id):
    with db().sesion() as s:
        p = s.get(Producto, producto_id)
        if p is None:
            raise ProductoNoEncontradoError(_("El producto {producto_id} no existe.", producto_id=producto_id))
        return jsonify(producto_json(p))


@bp.post("/productos")
def crear_producto():
    datos = json_entrada()
    invalido = SolicitudInvalidaError(_("Faltan campos o tienen un formato inválido."), "PRODUCTO_INVALIDO")
    try:
        tipo = str(datos["tipo"]).upper()
        precio = Decimal(str(datos["precio_base_m2"]))
        stock = Decimal(str(datos["stock_m2"]))
        calibre = int(datos["calibre_acero"])
        nombre = str(datos["nombre"]).strip()
    except Exception:
        raise invalido
    if tipo not in TIPOS or calibre not in (304, 430) or precio <= 0 or stock < 0 or not nombre:
        raise invalido
    with db().sesion() as s:
        p = Producto(nombre=nombre, tipo=tipo, calibre_acero=calibre, precio_base_m2=precio, stock_m2=stock)
        s.add(p)
        s.flush()
        return jsonify(producto_json(p)), 201
