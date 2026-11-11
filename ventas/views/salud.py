"""Healthchecks del monolito y estado del ecosistema completo."""
from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse

from ventas.domain.excepciones import ServicioNoDisponibleError
from ventas.infra.http import ClienteHttp, estado_circuitos


def salud_viva(request):
    """Liveness para el healthcheck de Docker (no depende de otros servicios)."""
    return JsonResponse({"servicio": "monolito-django", "estado": "ok"})


def salud(request):
    """Estado del ecosistema completo (util en la sustentacion)."""
    componentes = {}
    try:
        connection.ensure_connection()
        componentes["base_de_datos"] = "ok"
    except Exception:
        componentes["base_de_datos"] = "caido"
    try:
        cache.set("salud", "ok", 5)
        componentes["cache"] = "ok" if cache.get("salud") == "ok" else "caido"
    except Exception:
        componentes["cache"] = "caido"
    for nombre, url in settings.MICROSERVICIOS.items():
        ruta = f"/api/{nombre.lower()}/health"
        try:
            r = ClienteHttp(f"salud-{nombre.lower()}", url, timeout=2).get(ruta)
            componentes[f"ms_{nombre.lower()}"] = "ok" if r.status == 200 else f"HTTP {r.status}"
        except ServicioNoDisponibleError:
            componentes[f"ms_{nombre.lower()}"] = "caido"
    try:
        from monolito_venta_acero.celery import app
        respuesta = app.control.ping(timeout=1.0)
        componentes["celery_worker"] = "ok" if respuesta else "sin workers"
    except Exception:
        componentes["celery_worker"] = "caido"
    estado = "ok" if all(v == "ok" for v in componentes.values()) else "degradado"
    return JsonResponse({"estado": estado, "componentes": componentes, "circuitos": estado_circuitos()})
