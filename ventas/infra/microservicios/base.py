"""Utilidades compartidas por los adaptadores de microservicios."""
from ventas.domain.excepciones import ServicioNoDisponibleError
from ventas.infra.http import RespuestaHttp


def respuesta_inesperada(nombre: str, r: RespuestaHttp) -> ServicioNoDisponibleError:
    return ServicioNoDisponibleError(nombre, f"HTTP {r.status}")
