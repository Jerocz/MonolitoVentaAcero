"""
Patron Strategy: la logica de precio de cada tipo de producto vive aqui,
fuera de los modelos. Cada estrategia sabe calcular su precio y si el
producto se vende a la medida.
"""
from decimal import Decimal


class EstrategiaPrecio:
    """Contrato comun para todas las estrategias de precio."""
    ANCHO_MINIMO_CM = Decimal("60")
    es_a_medida = True

    def _area_m2(self, ancho_cm, largo_cm, cantidad):
        return (Decimal(str(ancho_cm)) / 100) * (Decimal(str(largo_cm)) / 100) * cantidad

    def calcular(self, precio_base_m2, ancho_cm, largo_cm, cantidad) -> Decimal:
        area = self._area_m2(ancho_cm, largo_cm, cantidad)
        return (precio_base_m2 * area).quantize(Decimal("0.01"))


class PrecioLamina(EstrategiaPrecio):
    """Precio = area * precio_base."""


class PrecioMeson(EstrategiaPrecio):
    """Precio con 15% adicional por refuerzos."""
    FACTOR = Decimal("1.15")

    def calcular(self, precio_base_m2, ancho_cm, largo_cm, cantidad):
        base = super().calcular(precio_base_m2, ancho_cm, largo_cm, cantidad)
        return (base * self.FACTOR).quantize(Decimal("0.01"))


class PrecioCampana(EstrategiaPrecio):
    """Precio por area + costo fijo de ducteria."""
    COSTO_DUCTERIA = Decimal("180000")

    def calcular(self, precio_base_m2, ancho_cm, largo_cm, cantidad):
        base = super().calcular(precio_base_m2, ancho_cm, largo_cm, cantidad)
        return (base + self.COSTO_DUCTERIA * cantidad).quantize(Decimal("0.01"))


class PrecioFreidora(EstrategiaPrecio):
    """Producto estandar: precio fijo por unidad, no es a la medida."""
    es_a_medida = False

    def calcular(self, precio_base_m2, ancho_cm, largo_cm, cantidad):
        return (precio_base_m2 * cantidad).quantize(Decimal("0.01"))


# Mapa tipo de producto -> su estrategia. Esto reemplaza al polimorfismo
# que antes vivia en los metodos del modelo.
_ESTRATEGIAS = {
    "LAMINA": PrecioLamina,
    "MESON": PrecioMeson,
    "CAMPANA": PrecioCampana,
    "FREIDORA": PrecioFreidora,
}


def estrategia_para(tipo: str) -> EstrategiaPrecio:
    return _ESTRATEGIAS.get(tipo, PrecioLamina)()
