from dataclasses import asdict

from rest_framework.response import Response
from rest_framework.views import APIView

from ventas.infra.contenedor import Contenedor


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
