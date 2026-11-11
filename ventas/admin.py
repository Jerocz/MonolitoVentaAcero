from django.contrib import admin

from ventas.models import Cliente, Cotizacion, ItemCotizacion, Notificacion, ReporteVentas

# Productos, ordenes y pagos ya no se administran aqui: son propiedad de
# ms-catalogo, ms-fabricacion y ms-pagos respectivamente.


class ItemCotizacionInline(admin.TabularInline):
    model = ItemCotizacion
    extra = 0


@admin.register(Cotizacion)
class CotizacionAdmin(admin.ModelAdmin):
    list_display = ("id", "cliente", "estado", "total", "anticipo", "orden_ref", "fecha_creacion")
    list_filter = ("estado",)
    inlines = [ItemCotizacionInline]


admin.site.register(Cliente)
admin.site.register(Notificacion)
admin.site.register(ReporteVentas)
