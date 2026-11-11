"""Crea los clientes de ejemplo.  Uso: python manage.py sembrar_datos

Los productos NO se crean aqui: el catalogo es propiedad de ms-catalogo, que
carga su catalogo inicial al arrancar (microservicios/ms_catalogo/app/init_db.py).
"""
from django.core.management.base import BaseCommand

from ventas.models import Cliente

CLIENTES = [
    ("Restaurante El Fogon", "900111-1", Cliente.Tipo.RESTAURANTE, "fogon@test.co"),
    ("Hotel Poblado", "900222-2", Cliente.Tipo.HOTEL, "hotel@test.co"),
    ("Camila Restrepo", "1017-555", Cliente.Tipo.PERSONA, "camila@test.co"),
    ("Andres Gil", "1020-777", Cliente.Tipo.PERSONA, "andres@test.co"),
    # Su correo hace que la pasarela simulada RECHACE el pago: sirve para
    # demostrar la compensacion de la saga (se libera el stock reservado).
    ("Cliente Prueba Rechazo", "000-000", Cliente.Tipo.PERSONA, "pagos@rechazo.test"),
]


class Command(BaseCommand):
    help = "Crea clientes de ejemplo si la base de datos no tiene ninguno."

    def handle(self, *args, **opciones):
        if Cliente.objects.exists():
            self.stdout.write("Ya hay clientes. No se crea nada.")
            return
        for nombre, documento, tipo, email in CLIENTES:
            Cliente.objects.create(nombre=nombre, nit_o_cedula=documento, tipo=tipo, email=email)
        self.stdout.write(self.style.SUCCESS(f"Clientes de ejemplo creados: {len(CLIENTES)}."))
