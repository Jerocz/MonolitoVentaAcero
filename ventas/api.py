"""Capa de Presentacion (DRF): APIViews.
Solo traducen HTTP <-> servicio y devuelven el codigo de estado correcto.
Sin logica de negocio (esa vive en los servicios y microservicios)."""
from dataclasses import asdict

from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from ventas.domain.excepciones import (
    OperacionNoPermitidaError,
    PagoRechazadoError,
    PedidoInvalidoError,
    RecursoNoEncontradoError,
    ServicioNoDisponibleError,
)
from ventas.infra.contenedor import Contenedor
from ventas.models import Cliente
from ventas.serializers import CotizacionSalidaSerializer, CrearCotizacionEntradaSerializer
from ventas.services import CotizacionService, OrdenService


def _no_disponible(e: ServicioNoDisponibleError):
    return Response({"error": _("Servicio no disponible: %(servicio)s") % {"servicio": e.servicio}},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE)


def _orden_json(orden):
    datos = asdict(orden)
    datos["total"] = str(orden.total)
    datos["fecha_estimada_entrega"] = orden.fecha_estimada_entrega.isoformat()
    return datos


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
            return _no_disponible(e)
        return Response(CotizacionSalidaSerializer(cotizacion).data, status=status.HTTP_201_CREATED)


class ProductoListAPIView(APIView):
    """Fachada: el catalogo real vive en ms-catalogo."""

    def get(self, request):
        try:
            productos = Contenedor.catalogo().listar_productos()
        except ServicioNoDisponibleError as e:
            return _no_disponible(e)
        return Response([{**asdict(p), "precio_base_m2": str(p.precio_base_m2), "stock_m2": str(p.stock_m2),
                          "ancho_minimo_cm": str(p.ancho_minimo_cm) if p.ancho_minimo_cm else None}
                         for p in productos])


class AvanzarEtapaAPIView(APIView):
    def post(self, request, orden_id):
        try:
            orden = OrdenService().avanzar_etapa(orden_id)
        except RecursoNoEncontradoError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except OperacionNoPermitidaError as e:
            return Response({"error": str(e)}, status=status.HTTP_409_CONFLICT)
        except ServicioNoDisponibleError as e:
            return _no_disponible(e)
        return Response(_orden_json(orden), status=status.HTTP_200_OK)


class PagarSaldoAPIView(APIView):
    def post(self, request, orden_id):
        try:
            orden = OrdenService().pagar_saldo(orden_id)
        except RecursoNoEncontradoError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except (PagoRechazadoError, OperacionNoPermitidaError) as e:
            return Response({"error": str(e)}, status=status.HTTP_409_CONFLICT)
        except ServicioNoDisponibleError as e:
            return _no_disponible(e)
        return Response(_orden_json(orden), status=status.HTTP_200_OK)


class TasaCambioAPIView(APIView):
    """Expone la tasa obtenida via el Adapter de la API de terceros."""

    def get(self, request):
        tasa = Contenedor.tasa_cambio().obtener("COP", "USD")
        return Response({"origen": tasa.origen, "destino": tasa.destino, "valor": str(tasa.valor),
                         "fuente": tasa.fuente, "es_respaldo": tasa.es_respaldo,
                         "actualizada": tasa.actualizada.isoformat() if tasa.actualizada else None})


class AliadoAPIView(APIView):
    """Lo que consumimos del equipo aliado, ya normalizado por el Adapter."""

    def get(self, request):
        return Response(asdict(Contenedor.aliado().consultar()))
