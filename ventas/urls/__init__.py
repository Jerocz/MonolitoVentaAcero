"""Rutas de la app ventas: paginas HTML (web.py) y API REST (api.py)."""
from django.urls import include, path

urlpatterns = [
    path("api/", include("ventas.urls.api")),
    path("", include("ventas.urls.web")),
]
