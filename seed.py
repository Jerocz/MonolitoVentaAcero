"""Crea clientes de ejemplo en el monolito. Ejecuta: python seed.py

Los productos ya NO se crean aqui: el catalogo es propiedad de ms-catalogo,
que carga su catalogo inicial al arrancar (microservicios/ms_catalogo/app/init_db.py).
"""
import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "monolito_venta_acero.settings")
django.setup()

from ventas.models import Cliente  # noqa: E402

CLIENTES = [
    ("Restaurante El Fogon", "900111-1", Cliente.Tipo.RESTAURANTE, "fogon@test.co"),
    ("Hotel Poblado", "900222-2", Cliente.Tipo.HOTEL, "hotel@test.co"),
    ("Camila Restrepo", "1017-555", Cliente.Tipo.PERSONA, "camila@test.co"),
    ("Andres Gil", "1020-777", Cliente.Tipo.PERSONA, "andres@test.co"),
    # Su correo hace que la pasarela simulada RECHACE el pago: sirve para
    # demostrar la compensacion de la saga (se libera el stock reservado).
    ("Cliente Prueba Rechazo", "000-000", Cliente.Tipo.PERSONA, "pagos@rechazo.test"),
]

if Cliente.objects.exists():
    print("Ya hay clientes. No se crea nada.")
else:
    for nombre, documento, tipo, email in CLIENTES:
        Cliente.objects.create(nombre=nombre, nit_o_cedula=documento, tipo=tipo, email=email)
    print(f"Clientes de ejemplo creados: {len(CLIENTES)}.")
