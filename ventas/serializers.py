"""Serializers de DRF: validan los datos de ENTRADA y arman los de SALIDA.
No contienen logica de negocio (eso vive en los servicios)."""
from rest_framework import serializers

from ventas.models import Cotizacion, OrdenFabricacion, Producto


# ---------- ENTRADA ----------
class ItemEntradaSerializer(serializers.Serializer):
    producto_id = serializers.IntegerField()
    ancho_cm = serializers.DecimalField(max_digits=6, decimal_places=1)
    largo_cm = serializers.DecimalField(max_digits=6, decimal_places=1)
    cantidad = serializers.IntegerField(min_value=1, default=1)


class CrearCotizacionEntradaSerializer(serializers.Serializer):
    cliente_id = serializers.IntegerField()
    items = ItemEntradaSerializer(many=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("Debe incluir al menos un item.")
        return value


# ---------- SALIDA ----------
class OrdenSalidaSerializer(serializers.ModelSerializer):
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)

    class Meta:
        model = OrdenFabricacion
        fields = ["id", "estado", "estado_display", "fecha_estimada_entrega"]


class CotizacionSalidaSerializer(serializers.ModelSerializer):
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)
    cliente = serializers.CharField(source="cliente.nombre", read_only=True)
    orden = OrdenSalidaSerializer(read_only=True)

    class Meta:
        model = Cotizacion
        fields = ["id", "cliente", "estado", "estado_display", "total",
                  "fecha_vencimiento", "orden"]


class ProductoSalidaSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)

    class Meta:
        model = Producto
        fields = ["id", "nombre", "tipo", "tipo_display", "precio_base_m2", "stock_m2"]
