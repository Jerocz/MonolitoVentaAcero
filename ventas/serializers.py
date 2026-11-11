"""Serializers de DRF: validan los datos de ENTRADA y arman los de SALIDA.
No contienen logica de negocio (eso vive en los servicios)."""
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from ventas.models import Cotizacion, ItemCotizacion


# ---------- ENTRADA ----------
class ItemEntradaSerializer(serializers.Serializer):
    producto_id = serializers.IntegerField(min_value=1)
    ancho_cm = serializers.DecimalField(max_digits=6, decimal_places=1)
    largo_cm = serializers.DecimalField(max_digits=6, decimal_places=1)
    cantidad = serializers.IntegerField(min_value=1, default=1)


class CrearCotizacionEntradaSerializer(serializers.Serializer):
    cliente_id = serializers.IntegerField()
    items = ItemEntradaSerializer(many=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError(_("Debe incluir al menos un ítem."))
        return value


# ---------- SALIDA ----------
class ItemSalidaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemCotizacion
        fields = ["producto_ref", "producto_nombre", "producto_tipo", "ancho_cm", "largo_cm",
                  "cantidad", "subtotal"]


class CotizacionSalidaSerializer(serializers.ModelSerializer):
    referencia = serializers.CharField(read_only=True)
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)
    cliente = serializers.CharField(source="cliente.nombre", read_only=True)
    items = ItemSalidaSerializer(many=True, read_only=True)

    class Meta:
        model = Cotizacion
        fields = ["id", "referencia", "cliente", "estado", "estado_display", "total", "anticipo",
                  "fecha_vencimiento", "orden_ref", "items"]
