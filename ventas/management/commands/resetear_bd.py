"""Reinicia la base de datos LOCAL (SQLite).  Uso: python manage.py resetear_bd

Solo para desarrollo sin Docker. Con Docker: `docker compose down -v`.
"""
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Borra la base SQLite local, aplica las migraciones y crea los clientes de ejemplo."

    def handle(self, *args, **opciones):
        base = settings.DATABASES["default"]
        if base["ENGINE"] != "django.db.backends.sqlite3":
            raise CommandError("Solo se permite con SQLite (desarrollo local).")
        call_command("flush", interactive=False)
        call_command("migrate", interactive=False)
        call_command("sembrar_datos")
        self.stdout.write(self.style.SUCCESS("Listo. Ejecuta: python manage.py runserver"))
