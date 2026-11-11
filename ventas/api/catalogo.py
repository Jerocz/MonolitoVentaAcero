from dataclasses import asdict

from rest_framework.response import Response
from rest_framework.views import APIView

from ventas.api.respuestas import no_disponible
from ventas.domain.excepciones import ServicioNoDisponibleError
from ventas.infra.contenedor import Contenedor


class ProductoListAPIView(APIView):
    """Fachada: el catalogo real vive en ms-catalogo."""

    def get(self, request):
        try:
            productos = Contenedor.catalogo().listar_productos()
        except ServicioNoDisponibleError as e:
            return no_disponible(e)
        return Response([{**asdict(p), "precio_base_m2": str(p.precio_base_m2), "stock_m2": str(p.stock_m2),
                          "ancho_minimo_cm": str(p.ancho_minimo_cm) if p.ancho_minimo_cm else None}
                         for p in productos])
