from django.contrib import admin

from ventas.models import (
    Campana,
    Cliente,
    Cotizacion,
    Freidora,
    ItemCotizacion,
    Lamina,
    Meson,
    OrdenFabricacion,
    Pago,
)

# Registramos las SUBCLASES concretas para poder crearlas desde el admin.
# (No registramos Producto base: siempre se crea un tipo concreto.)
admin.site.register(Cliente)
admin.site.register(Lamina)
admin.site.register(Meson)
admin.site.register(Campana)
admin.site.register(Freidora)
admin.site.register(Cotizacion)
admin.site.register(ItemCotizacion)
admin.site.register(OrdenFabricacion)
admin.site.register(Pago)
