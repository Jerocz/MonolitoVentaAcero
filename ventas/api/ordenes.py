from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from ventas.api.respuestas import no_disponible, orden_json
from ventas.domain.excepciones import (
    OperacionNoPermitidaError,
    PagoRechazadoError,
    RecursoNoEncontradoError,
    ServicioNoDisponibleError,
)
from ventas.services import OrdenService


class AvanzarEtapaAPIView(APIView):
    def post(self, request, orden_id):
        try:
            orden = OrdenService().avanzar_etapa(orden_id)
        except RecursoNoEncontradoError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except OperacionNoPermitidaError as e:
            return Response({"error": str(e)}, status=status.HTTP_409_CONFLICT)
        except ServicioNoDisponibleError as e:
            return no_disponible(e)
        return Response(orden_json(orden), status=status.HTTP_200_OK)


class PagarSaldoAPIView(APIView):
    def post(self, request, orden_id):
        try:
            orden = OrdenService().pagar_saldo(orden_id)
        except RecursoNoEncontradoError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except (PagoRechazadoError, OperacionNoPermitidaError) as e:
            return Response({"error": str(e)}, status=status.HTTP_409_CONFLICT)
        except ServicioNoDisponibleError as e:
            return no_disponible(e)
        return Response(orden_json(orden), status=status.HTTP_200_OK)
