from django.conf import settings


def empresa(request):
    """Datos de contacto de la empresa disponibles en todas las plantillas
    (asi no quedan quemados en el HTML)."""
    return {"empresa": settings.EMPRESA}
