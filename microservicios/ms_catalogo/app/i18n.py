"""Internacionalizacion del microservicio con gettext (biblioteca estandar).

Los textos fuente estan en espanol y se traducen con los catalogos
`locales/<idioma>/LC_MESSAGES/messages.po|.mo`. El idioma se elige con el
encabezado `Accept-Language` que envian el monolito o el navegador.
"""
import gettext
from pathlib import Path

from flask import has_request_context, request

DOMINIO = "messages"
CARPETA_LOCALES = Path(__file__).resolve().parent / "locales"
IDIOMAS = ("es", "en")
IDIOMA_POR_DEFECTO = "es"

_catalogos = {
    idioma: gettext.translation(DOMINIO, localedir=CARPETA_LOCALES, languages=[idioma], fallback=True)
    for idioma in IDIOMAS
}


def idioma_actual() -> str:
    if not has_request_context():
        return IDIOMA_POR_DEFECTO
    return request.accept_languages.best_match(IDIOMAS) or IDIOMA_POR_DEFECTO


def _(mensaje: str, **valores) -> str:
    """Traduce `mensaje` al idioma de la peticion e interpola `{valores}`."""
    texto = _catalogos[idioma_actual()].gettext(mensaje)
    return texto.format(**valores) if valores else texto
