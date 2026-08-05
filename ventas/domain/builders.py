"""Patron Builder: construye y valida la Cotizacion antes de guardarla."""
from datetime import date, timedelta
from decimal import Decimal

from ventas.domain.excepciones import PedidoInvalidoError
from ventas.models import Cotizacion, ItemCotizacion, ProductoAMedida

DIAS_VIGENCIA = 15


class CotizacionBuilder:
    def __init__(self):
        self._cliente = None
        self._items = []

    def para_cliente(self, cliente):
        self._cliente = cliente
        return self

    def con_item(self, producto, ancho_cm, largo_cm, cantidad=1):
        self._items.append({
            "producto": producto.instancia_real(),
            "ancho": Decimal(str(ancho_cm)),
            "largo": Decimal(str(largo_cm)),
            "cantidad": int(cantidad),
        })
        return self

    def _validar(self):
        if self._cliente is None:
            raise PedidoInvalidoError("La cotizacion necesita un cliente.")
        if not self._items:
            raise PedidoInvalidoError("La cotizacion debe tener al menos un item.")
        for item in self._items:
            producto = item["producto"]
            if isinstance(producto, ProductoAMedida):
                if not producto.validar_medidas_minimas(item["ancho"]):
                    raise PedidoInvalidoError(
                        f"'{producto.nombre}': el ancho minimo es {producto.ANCHO_MINIMO_CM} cm.")
            if item["largo"] <= 0 or item["cantidad"] <= 0:
                raise PedidoInvalidoError("Medidas y cantidad deben ser positivas.")
            area = self._area_m2(item)
            if not producto.hay_stock_para(area):
                raise PedidoInvalidoError(
                    f"'{producto.nombre}': stock insuficiente (pide {area:.2f} m2, hay {producto.stock_m2} m2).")

    def _area_m2(self, item):
        return (item["ancho"] / 100) * (item["largo"] / 100) * item["cantidad"]

    def build(self):
        self._validar()
        cotizacion = Cotizacion.objects.create(
            cliente=self._cliente,
            fecha_vencimiento=date.today() + timedelta(days=DIAS_VIGENCIA),
        )
        total = Decimal("0")
        for item in self._items:
            producto = item["producto"]
            subtotal = producto.calcular_precio(item["ancho"], item["largo"], item["cantidad"])
            ItemCotizacion.objects.create(
                cotizacion=cotizacion, producto=producto, ancho_cm=item["ancho"],
                largo_cm=item["largo"], cantidad=item["cantidad"], subtotal=subtotal)
            producto.descontar_stock(self._area_m2(item))
            total += subtotal
        cotizacion.total = total
        cotizacion.save(update_fields=["total"])
        return cotizacion
