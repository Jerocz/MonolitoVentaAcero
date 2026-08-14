"""Capa de Presentacion (DRF): APIViews.
Solo traducen HTTP <-> servicio y devuelven el codigo de estado correcto.
Sin logica de negocio (esa vive en los servicios)."""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from ventas.domain.excepciones import PagoRechazadoError, PedidoInvalidoError
from ventas.models import Cliente, OrdenFabricacion, Producto
from ventas.serializers import (
    CotizacionSalidaSerializer,
    CrearCotizacionEntradaSerializer,
    OrdenSalidaSerializer,
    ProductoSalidaSerializer,
)
from ventas.services import CotizacionService, OrdenService


class CrearCotizacionAPIView(APIView):
    def post(self, request):
        entrada = CrearCotizacionEntradaSerializer(data=request.data)
        if not entrada.is_valid():
            return Response(entrada.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            cotizacion = CotizacionService().crear_cotizacion(
                cliente_id=entrada.validated_data["cliente_id"],
                items=entrada.validated_data["items"])
        except (Cliente.DoesNotExist, Producto.DoesNotExist):
            return Response({"error": "Cliente o producto no existe."},
                            status=status.HTTP_404_NOT_FOUND)
        except PedidoInvalidoError as e:
            return Response({"error": str(e)}, status=status.HTTP_409_CONFLICT)
        except PagoRechazadoError as e:
            return Response({"error": str(e)}, status=status.HTTP_409_CONFLICT)
        salida = CotizacionSalidaSerializer(cotizacion)
        return Response(salida.data, status=status.HTTP_201_CREATED)


class ProductoListAPIView(APIView):
    def get(self, request):
        productos = Producto.objects.all()
        return Response(ProductoSalidaSerializer(productos, many=True).data)


class AvanzarEtapaAPIView(APIView):
    def post(self, request, orden_id):
        try:
            orden = OrdenService().avanzar_etapa(orden_id)
        except OrdenFabricacion.DoesNotExist:
            return Response({"error": "Orden no existe."}, status=status.HTTP_404_NOT_FOUND)
        return Response(OrdenSalidaSerializer(orden).data, status=status.HTTP_200_OK)


class PagarSaldoAPIView(APIView):
    def post(self, request, orden_id):
        try:
            orden = OrdenService().pagar_saldo(orden_id)
        except OrdenFabricacion.DoesNotExist:
            return Response({"error": "Orden no existe."}, status=status.HTTP_404_NOT_FOUND)
        except PagoRechazadoError as e:
            return Response({"error": str(e)}, status=status.HTTP_409_CONFLICT)
        return Response(OrdenSalidaSerializer(orden).data, status=status.HTTP_200_OK)
