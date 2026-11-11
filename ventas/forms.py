"""Formularios robustos: validan en el servidor ANTES de llamar a los
microservicios y devuelven errores por campo, traducidos y entendibles."""
from decimal import Decimal

from django import forms
from django.utils.translation import gettext_lazy as _

MEDIDA_MAXIMA_CM = Decimal("1000")
CANTIDAD_MAXIMA = 50


class CotizacionForm(forms.Form):
    cliente_id = forms.TypedChoiceField(
        label=_("Cliente"), coerce=int,
        error_messages={"required": _("Elige el cliente que hace el pedido."),
                        "invalid_choice": _("El cliente elegido no existe.")})
    producto_id = forms.TypedChoiceField(
        label=_("Producto"), coerce=int,
        error_messages={"required": _("Elige un producto del catálogo."),
                        "invalid_choice": _("El producto elegido no existe.")})
    ancho_cm = forms.DecimalField(
        label=_("Ancho (cm)"), max_digits=6, decimal_places=1, min_value=Decimal("0.1"),
        max_value=MEDIDA_MAXIMA_CM, initial=Decimal("70"),
        error_messages={"required": _("Escribe el ancho en centímetros."),
                        "invalid": _("El ancho debe ser un número, por ejemplo 70 o 70.5.")})
    largo_cm = forms.DecimalField(
        label=_("Largo (cm)"), max_digits=6, decimal_places=1, min_value=Decimal("0.1"),
        max_value=MEDIDA_MAXIMA_CM, initial=Decimal("150"),
        error_messages={"required": _("Escribe el largo en centímetros."),
                        "invalid": _("El largo debe ser un número, por ejemplo 150.")})
    cantidad = forms.IntegerField(
        label=_("Cantidad"), min_value=1, max_value=CANTIDAD_MAXIMA, initial=1,
        error_messages={"required": _("Indica cuántas unidades necesitas."),
                        "invalid": _("La cantidad debe ser un número entero.")})

    def __init__(self, *args, clientes=(), productos=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.productos = {p.id: p for p in productos}
        self.fields["cliente_id"].choices = [("", _("Selecciona un cliente…"))] + [
            (c.id, f"{c.nombre} — {c.get_tipo_display()}") for c in clientes]
        self.fields["producto_id"].choices = [("", _("Selecciona un producto…"))] + [
            (p.id, p.nombre) for p in productos]

    def clean(self):
        datos = super().clean()
        producto = self.productos.get(datos.get("producto_id"))
        ancho = datos.get("ancho_cm")
        if producto and producto.es_a_medida and ancho is not None and producto.ancho_minimo_cm \
                and ancho < producto.ancho_minimo_cm:
            self.add_error("ancho_cm", _("Para %(producto)s el ancho mínimo es %(minimo)s cm.") % {
                "producto": producto.nombre, "minimo": f"{producto.ancho_minimo_cm:.0f}"})
        return datos

    def como_items(self) -> list[dict]:
        d = self.cleaned_data
        return [{"producto_id": d["producto_id"], "ancho_cm": d["ancho_cm"],
                 "largo_cm": d["largo_cm"], "cantidad": d["cantidad"]}]

