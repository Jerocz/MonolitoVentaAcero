"""Patron Strategy (migrado desde el monolito: ventas/domain/precios.py).

Cada tipo de producto sabe calcular su precio, si se vende a la medida y
cuanto stock consume. Agregar un tipo nuevo = agregar una estrategia.
"""
from decimal import Decimal

CENTAVOS = Decimal("0.01")


def area_m2(ancho_cm, largo_cm, cantidad) -> Decimal:
    return (Decimal(ancho_cm) / 100) * (Decimal(largo_cm) / 100) * cantidad


class EstrategiaPrecio:
    """Contrato comun para todas las estrategias de precio."""
    ANCHO_MINIMO_CM = Decimal("60")
    es_a_medida = True
    unidad = "m2"

    def calcular(self, precio_base_m2, ancho_cm, largo_cm, cantidad) -> Decimal:
        return (Decimal(precio_base_m2) * area_m2(ancho_cm, largo_cm, cantidad)).quantize(CENTAVOS)

    def consumo_stock(self, ancho_cm, largo_cm, cantidad) -> Decimal:
        """Cuanto stock gasta el item (m2 para productos a la medida)."""
        return area_m2(ancho_cm, largo_cm, cantidad).quantize(Decimal("0.0001"))


class PrecioLamina(EstrategiaPrecio):
    """Precio = area * precio_base."""


class PrecioMeson(EstrategiaPrecio):
    """Precio con 15% adicional por refuerzos."""
    FACTOR = Decimal("1.15")

    def calcular(self, precio_base_m2, ancho_cm, largo_cm, cantidad):
        base = super().calcular(precio_base_m2, ancho_cm, largo_cm, cantidad)
        return (base * self.FACTOR).quantize(CENTAVOS)


class PrecioCampana(EstrategiaPrecio):
    """Precio por area + costo fijo de ducteria por unidad."""
    COSTO_DUCTERIA = Decimal("180000")

    def calcular(self, precio_base_m2, ancho_cm, largo_cm, cantidad):
        base = super().calcular(precio_base_m2, ancho_cm, largo_cm, cantidad)
        return (base + self.COSTO_DUCTERIA * cantidad).quantize(CENTAVOS)


class PrecioFreidora(EstrategiaPrecio):
    """Producto estandar: precio fijo por unidad, no es a la medida."""
    es_a_medida = False
    unidad = "unidad"

    def calcular(self, precio_base_m2, ancho_cm, largo_cm, cantidad):
        return (Decimal(precio_base_m2) * cantidad).quantize(CENTAVOS)

    def consumo_stock(self, ancho_cm, largo_cm, cantidad):
        return Decimal(cantidad)


_ESTRATEGIAS = {
    "LAMINA": PrecioLamina,
    "MESON": PrecioMeson,
    "CAMPANA": PrecioCampana,
    "FREIDORA": PrecioFreidora,
}

TIPOS = tuple(_ESTRATEGIAS)


def estrategia_para(tipo: str) -> EstrategiaPrecio:
    return _ESTRATEGIAS.get(tipo, PrecioLamina)()
