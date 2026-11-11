from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from ventas.api.respuestas import no_disponible
from ventas.api.serializadores import CotizacionSalidaSerializer, CrearCotizacionEntradaSerializer
from ventas.domain.excepciones import (
    PagoRechazadoError,
    PedidoInvalidoError,
    RecursoNoEncontradoError,
    ServicioNoDisponibleError,
)
from ventas.models import Cliente
from ventas.services import CotizacionService


class CrearCotizacionAPIView(APIView):
    def post(self, request):
        entrada = CrearCotizacionEntradaSerializer(data=request.data)
        if not entrada.is_valid():
            return Response(entrada.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            cotizacion = CotizacionService().crear_cotizacion(
                cliente_id=entrada.validated_data["cliente_id"],
                items=entrada.validated_data["items"])
        except Cliente.DoesNotExist:
            return Response({"error": _("El cliente no existe.")}, status=status.HTTP_404_NOT_FOUND)
        except RecursoNoEncontradoError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except (PedidoInvalidoError, PagoRechazadoError) as e:
            return Response({"error": str(e)}, status=status.HTTP_409_CONFLICT)
        except ServicioNoDisponibleError as e:
            return no_disponible(e)
        return Response(CotizacionSalidaSerializer(cotizacion).data, status=status.HTTP_201_CREATED)
