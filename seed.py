"""Crea datos de ejemplo para ver la pagina con contenido. Ejecuta: python seed.py"""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "monolito_venta_acero.settings")
django.setup()

from ventas.models import Campana, Cliente, Freidora, Lamina, Meson

if Cliente.objects.exists():
    print("Ya hay datos. No se crea nada.")
else:
    Cliente.objects.create(nombre="Restaurante El Fogon", nit_o_cedula="900111-1", tipo=Cliente.Tipo.RESTAURANTE, email="fogon@test.co")
    Cliente.objects.create(nombre="Hotel Poblado", nit_o_cedula="900222-2", tipo=Cliente.Tipo.HOTEL, email="hotel@test.co")
    Lamina.objects.create(nombre="Lamina 304", calibre_acero=304, precio_base_m2=120000, stock_m2=60)
    Meson.objects.create(nombre="Meson central", calibre_acero=304, precio_base_m2=120000, stock_m2=60)
    Campana.objects.create(nombre="Campana extractora", calibre_acero=430, precio_base_m2=90000, stock_m2=60)
    Freidora.objects.create(nombre="Freidora 2 canastas", calibre_acero=304, precio_base_m2=1500000, stock_m2=99)
    print("Datos de ejemplo creados: 2 clientes y 4 productos.")
