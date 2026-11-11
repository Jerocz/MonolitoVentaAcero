"""Internacionalizacion: soporte bilingue y prohibicion de textos quemados."""
import re
from pathlib import Path

import polib
from django.conf import settings
from django.template.base import Lexer, TokenType
from django.test import SimpleTestCase
from django.urls import reverse
from django.utils import translation

from ventas.models import Cliente, Cotizacion
from ventas.tests.dobles import ConDobles

CARPETA_PLANTILLAS = Path(settings.BASE_DIR) / "ventas" / "templates"
# Unidades, normas y codigos que no dependen del idioma.
PERMITIDOS = {"AISI", "m²", "US", "COP", "USD", "GET"}
SCRIPTS_Y_ESTILOS = re.compile(r"<(script|style)\b.*?</\1>", re.S)
COMENTARIOS = re.compile(r"<!--.*?-->", re.S)
ETIQUETAS = re.compile(r"<[^>]*>")
ENTIDADES = re.compile(r"&\w+;")
PALABRAS = re.compile(r"[^\W\d_]{2,}")


def textos_quemados(ruta: Path) -> list[str]:
    """Devuelve el texto visible que NO pasa por {% translate %} / {% blocktranslate %}."""
    partes, en_bloque_traducido = [], 0
    for token in Lexer(ruta.read_text(encoding="utf-8")).tokenize():
        if token.token_type == TokenType.BLOCK:
            nombre = token.contents.split()[0]
            if nombre in ("blocktranslate", "blocktrans"):
                en_bloque_traducido += 1
            elif nombre in ("endblocktranslate", "endblocktrans"):
                en_bloque_traducido -= 1
        if token.token_type == TokenType.TEXT and not en_bloque_traducido:
            partes.append(token.contents)
        else:
            partes.append(" ")  # etiquetas de Django y texto ya traducido
    html = COMENTARIOS.sub(" ", SCRIPTS_Y_ESTILOS.sub(" ", "".join(partes)))
    visible = ENTIDADES.sub(" ", ETIQUETAS.sub(" ", html))  # sin etiquetas HTML ni atributos
    return [p for p in PALABRAS.findall(visible) if p not in PERMITIDOS]


class SinTextosQuemadosTest(SimpleTestCase):
    def test_el_detector_encuentra_textos_quemados(self):
        ruta = Path(settings.BASE_DIR) / "ventas" / "tests" / "_plantilla_prueba.html"
        ruta.write_text('{% load i18n %}<p title="x">Hola {{ v }}</p>{% translate "ok" %}'
                        '<script>var z = "js";</script>', encoding="utf-8")
        self.addCleanup(ruta.unlink)
        self.assertEqual(textos_quemados(ruta), ["Hola"])

    def test_ninguna_plantilla_tiene_textos_quemados(self):
        plantillas = list(CARPETA_PLANTILLAS.rglob("*.html"))
        self.assertGreater(len(plantillas), 3)
        for ruta in plantillas:
            with self.subTest(plantilla=ruta.name):
                self.assertEqual(textos_quemados(ruta), [])

    def test_catalogo_ingles_completo(self):
        po = polib.pofile(str(Path(settings.BASE_DIR) / "locale" / "en" / "LC_MESSAGES" / "django.po"))
        self.assertEqual(po.untranslated_entries(), [])
        self.assertEqual(po.fuzzy_entries(), [])
        self.assertGreater(len(po.translated_entries()), 100)


class PaginaBilingueTest(ConDobles):
    def test_pagina_en_ingles(self):
        r = self.client.get(reverse("cotizacion_form"), HTTP_ACCEPT_LANGUAGE="en")
        self.assertContains(r, 'lang="en"')
        self.assertContains(r, "Custom-cut stainless steel")
        self.assertContains(r, "Quote and pay the 50% down payment")
        self.assertNotContains(r, "Cotiza a la medida")
        self.assertNotContains(r, "%%")

    def test_pagina_en_espanol(self):
        r = self.client.get(reverse("cotizacion_form"), HTTP_ACCEPT_LANGUAGE="es")
        self.assertContains(r, "Cotiza a la medida")
        self.assertContains(r, "Cotizar y pagar anticipo del 50%")
        self.assertNotContains(r, "%%")

    def test_selector_de_idioma_cambia_y_recuerda(self):
        self.client.post(reverse("set_language"), {"language": "en", "next": "/"})
        r = self.client.get(reverse("cotizacion_form"))
        self.assertContains(r, 'lang="en"')

    def test_estados_de_modelo_traducidos(self):
        cliente = Cliente.objects.create(nombre="X", nit_o_cedula="1", email="x@test.co")
        cot = Cotizacion.objects.create(cliente=cliente, fecha_vencimiento="2026-12-01",
                                        estado=Cotizacion.Estado.APROBADA)
        with translation.override("en"):
            self.assertEqual(cot.get_estado_display(), "Approved")

    def test_errores_de_formulario_traducidos(self):
        cliente = Cliente.objects.create(nombre="X", nit_o_cedula="1", email="x@test.co")
        r = self.client.post(reverse("cotizacion_form"), {
            "cliente_id": cliente.id, "producto_id": 1, "ancho_cm": "x", "largo_cm": "150", "cantidad": "1"},
            HTTP_ACCEPT_LANGUAGE="en")
        self.assertContains(r, "The width must be a number", status_code=400)
