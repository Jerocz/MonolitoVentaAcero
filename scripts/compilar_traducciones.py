"""Compila todos los catalogos gettext (.po -> .mo) del repositorio.

Equivale a `msgfmt` / `python manage.py compilemessages`, pero funciona en
Windows sin instalar GNU gettext (usa la libreria `polib`).

Uso:  pip install polib && python scripts/compilar_traducciones.py
"""
from pathlib import Path

import polib

RAIZ = Path(__file__).resolve().parent.parent
EXCLUIR = {".venv", "venv", "node_modules", ".git", "staticfiles"}


def main():
    total = 0
    for po_path in RAIZ.rglob("*.po"):
        if EXCLUIR & set(po_path.parts):
            continue
        po = polib.pofile(str(po_path))
        po.save_as_mofile(str(po_path.with_suffix(".mo")))
        total += 1
        print(f"{po_path.relative_to(RAIZ)}  ->  {po.percent_translated()}% traducido")
    print(f"{total} catalogos compilados.")


if __name__ == "__main__":
    main()
