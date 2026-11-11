"""Reinicia la base de datos LOCAL (SQLite) del monolito. Uso: python resetear_bd.py

Solo para desarrollo sin Docker. Con Docker: `docker compose down -v`.
"""
import os
import subprocess
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "monolito_venta_acero.settings")

if os.path.exists("db.sqlite3"):
    os.remove("db.sqlite3")

import django  # noqa: E402

django.setup()
from django.core.management import call_command  # noqa: E402

call_command("migrate")
subprocess.run([sys.executable, "seed.py"], check=True)
print("Listo. Ejecuta: python manage.py runserver")
