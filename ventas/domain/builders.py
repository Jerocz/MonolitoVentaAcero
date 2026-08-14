"""Patron Builder: construye y valida la Cotizacion antes de guardarla.
Usa las estrategias de precio; no depende de logica en los modelos."""
from datetime import date, timedelta
from decimal import Decimal

from ventas.domain.excepciones import PedidoInvalidoError
from ventas.domain.precios import estrategia_para
from ventas.domain.reglas import DIAS_VIGENCIA_COTIZACION
from ventas.models import Cotizacion, ItemCotizacion


class CotizacionBuilder:
    def __init__(self):
        self._cliente = None
        self._items = []

    def para_cliente(self, cliente):
        self._cliente = cliente
        return self

    def con_item(self, producto, ancho_cm, largo_cm, cantidad=1):
        self._items.append({
            "producto": producto,
            "ancho": Decimal(str(ancho_cm)),
            "largo": Decimal(str(largo_cm)),
            "cantidad": int(cantidad),
        })
        return self

    def _area_m2(self, item):
        return (item["ancho"] / 100) * (item["largo"] / 100) * item["cantidad"]

    def _validar(self):
        if self._cliente is None:
            raise PedidoInvalidoError("La cotizacion necesita un cliente.")
        if not self._items:
            raise PedidoInvalidoError("La cotizacion debe tener al menos un item.")
        for item in self._items:
            producto = item["producto"]
            estrategia = estrategia_para(producto.tipo)
            if estrategia.es_a_medida and item["ancho"] < estrategia.ANCHO_MINIMO_CM:
                raise PedidoInvalidoError(
                    f"'{producto.nombre}': el ancho minimo es {estrategia.ANCHO_MINIMO_CM} cm.")
            if item["largo"] <= 0 or item["cantidad"] <= 0:
                raise PedidoInvalidoError("Medidas y cantidad deben ser positivas.")
            area = self._area_m2(item)
            if producto.stock_m2 < area:
                raise PedidoInvalidoError(
                    f"'{producto.nombre}': stock insuficiente (pide {area:.2f} m2, hay {producto.stock_m2} m2).")

    def build(self):
        self._validar()
        cotizacion = Cotizacion.objects.create(
            cliente=self._cliente,
            fecha_vencimiento=date.today() + timedelta(days=DIAS_VIGENCIA_COTIZACION),
        )
        total = Decimal("0")
        for item in self._items:
            producto = item["producto"]
            estrategia = estrategia_para(producto.tipo)
            subtotal = estrategia.calcular(
                producto.precio_base_m2, item["ancho"], item["largo"], item["cantidad"])
            ItemCotizacion.objects.create(
                cotizacion=cotizacion, producto=producto, ancho_cm=item["ancho"],
                largo_cm=item["largo"], cantidad=item["cantidad"], subtotal=subtotal)
            producto.stock_m2 -= self._area_m2(item)
            producto.save(update_fields=["stock_m2"])
            total += subtotal
        cotizacion.total = total
        cotizacion.save(update_fields=["total"])
        return cotizacion
