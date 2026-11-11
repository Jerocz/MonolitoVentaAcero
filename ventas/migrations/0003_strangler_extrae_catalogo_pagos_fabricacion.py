"""Strangler Pattern: el catalogo, las ordenes y los pagos pasan a ser
propiedad de los microservicios. Antes de borrar las tablas se copian a la
cotizacion los datos que el monolito necesita seguir mostrando."""
from django.db import migrations, models


def copiar_referencias(apps, schema_editor):
    ItemCotizacion = apps.get_model("ventas", "ItemCotizacion")
    Producto = apps.get_model("ventas", "Producto")
    OrdenFabricacion = apps.get_model("ventas", "OrdenFabricacion")
    Pago = apps.get_model("ventas", "Pago")
    Cotizacion = apps.get_model("ventas", "Cotizacion")

    productos = {p.id: p for p in Producto.objects.all()}
    for item in ItemCotizacion.objects.all():
        p = productos.get(item.producto_id)
        ItemCotizacion.objects.filter(pk=item.pk).update(
            producto_ref=item.producto_id,
            producto_nombre=p.nombre if p else "",
            producto_tipo=p.tipo if p else "")
    for orden in OrdenFabricacion.objects.all():
        anticipo = Pago.objects.filter(orden_id=orden.id, tipo="ANTICIPO", aprobado=True).first()
        Cotizacion.objects.filter(pk=orden.cotizacion_id).update(
            orden_ref=orden.id, anticipo=anticipo.monto if anticipo else 0)


class Migration(migrations.Migration):

    dependencies = [
        ("ventas", "0002_alter_cotizacion_total_alter_itemcotizacion_ancho_cm_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="cotizacion", name="anticipo",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=14)),
        migrations.AddField(
            model_name="cotizacion", name="orden_ref",
            field=models.PositiveIntegerField(blank=True, null=True)),
        migrations.AddField(
            model_name="itemcotizacion", name="producto_ref",
            field=models.PositiveIntegerField(default=0), preserve_default=False),
        migrations.AddField(
            model_name="itemcotizacion", name="producto_nombre",
            field=models.CharField(default="", max_length=120), preserve_default=False),
        migrations.AddField(
            model_name="itemcotizacion", name="producto_tipo",
            field=models.CharField(default="", max_length=10), preserve_default=False),
        migrations.RunPython(copiar_referencias, migrations.RunPython.noop),
        migrations.RemoveField(model_name="itemcotizacion", name="producto"),
        migrations.DeleteModel(name="Pago"),
        migrations.DeleteModel(name="OrdenFabricacion"),
        migrations.DeleteModel(name="Campana"),
        migrations.DeleteModel(name="Freidora"),
        migrations.DeleteModel(name="Lamina"),
        migrations.DeleteModel(name="Meson"),
        migrations.DeleteModel(name="Producto"),
    ]
