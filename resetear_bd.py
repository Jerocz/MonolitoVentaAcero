"""Reinicia la base de datos desde cero. Uso: python resetear_bd.py"""
import glob
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "monolito_venta_acero.settings")

if os.path.exists("db.sqlite3"):
    os.remove("db.sqlite3")
for f in glob.glob("ventas/migrations/0*.py"):
    os.remove(f)

import django
django.setup()
from django.core.management import call_command
call_command("makemigrations", "ventas")
call_command("migrate")

from ventas.models import Campana, Cliente, Freidora, Lamina, Meson
if not Cliente.objects.exists():
    Cliente.objects.create(nombre="Restaurante El Fogon", nit_o_cedula="900111-1", tipo=Cliente.Tipo.RESTAURANTE, email="fogon@test.co")
    Cliente.objects.create(nombre="Hotel Poblado", nit_o_cedula="900222-2", tipo=Cliente.Tipo.HOTEL, email="hotel@test.co")
    Lamina.objects.create(nombre="Lamina 304", calibre_acero=304, precio_base_m2=120000, stock_m2=60)
    Meson.objects.create(nombre="Meson central", calibre_acero=304, precio_base_m2=120000, stock_m2=60)
    Campana.objects.create(nombre="Campana extractora", calibre_acero=430, precio_base_m2=90000, stock_m2=60)
    Freidora.objects.create(nombre="Freidora 2 canastas", calibre_acero=304, precio_base_m2=1500000, stock_m2=99)
print("Listo. Ejecuta: python manage.py runserver")
