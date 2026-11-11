# Auditoría de UI/UX e internacionalización

## Hallazgos y correcciones (heurísticas de Nielsen)

| # | Hallazgo en la Entrega 1 | Heurística | Corrección |
|---|---|---|---|
| 1 | Recargar la página después de cotizar volvía a enviar el formulario y **cobraba el anticipo otra vez** | Prevención de errores | Patrón Post/Redirect/Get: tras cotizar se redirige a `/?cotizacion=<id>` |
| 2 | Doble clic en "Cotizar" podía crear dos cotizaciones | Prevención de errores | `app.js` deshabilita el botón y muestra "Procesando pago…"; además los microservicios son idempotentes |
| 3 | "Pagar saldo" cobraba sin confirmar | Control y libertad del usuario | Confirmación (`data-confirm`) con el número de orden |
| 4 | Errores genéricos arriba del formulario, sin decir qué campo falló | Ayudar a reconocer y corregir errores | `CotizacionForm` con mensajes por campo, `aria-invalid`, `aria-describedby` y foco automático en el primer error |
| 5 | Medidas no numéricas o cantidad 0 llegaban al servicio | Prevención de errores | Validación en servidor (tipos, mínimos y máximos) y en el navegador (`min`, `max`, `step`, `inputmode`) |
| 6 | Los valores escritos se perdían al haber un error | Reconocer antes que recordar | El formulario conserva lo que escribió el usuario |
| 7 | Avanzar etapa / pagar saldo no daba ninguna respuesta | Visibilidad del estado del sistema | Mensajes de éxito/error (`django.contrib.messages`) en una región `aria-live` |
| 8 | En celular el menú de navegación desaparecía | Flexibilidad | Menú desplazable horizontalmente en pantallas < 820 px; tablas con scroll |
| 9 | Si un servicio fallaba, la página daba error 500 | Visibilidad / prevención | Degradación controlada: la página carga y avisa qué servicio no está disponible |
| 10 | Labels sin `for`, sin "saltar al contenido", foco poco visible | Accesibilidad | `<label for>`, enlace "Saltar al contenido", `:focus-visible`, `caption` y `scope` en tablas |
| 11 | Textos, teléfono y correo quemados en el HTML | Consistencia | Todo pasa por gettext; los datos de la empresa vienen de `settings.EMPRESA` |
| 12 | Sin páginas de error propias | Consistencia | Plantillas `404.html` y `500.html` traducidas |

## Internacionalización (gettext)

* **Django**: `LocaleMiddleware`, `LANGUAGES = es/en`, `LOCALE_PATHS = locale/`.
  Plantillas con `{% translate %}` / `{% blocktranslate %}`; Python con
  `gettext` / `gettext_lazy` (modelos, choices, formularios, mensajes, correos,
  encabezados del CSV).
* **Selector de idioma** en el encabezado (vista `set_language` de Django); el
  idioma se recuerda en la cookie.
* **Microservicios Flask**: `gettext` de la biblioteca estándar
  (`app/i18n.py`) con catálogos `app/locales/en/LC_MESSAGES/messages.po`. El
  monolito propaga el idioma con el encabezado `Accept-Language`, así que los
  errores de negocio (ancho mínimo, stock, etapas) llegan ya traducidos.
* **Tareas de Celery**: reciben el idioma del usuario y usan `translation.override`.
* **Prohibido texto quemado — verificado automáticamente**:
  `ventas/tests/test_i18n.py` recorre todas las plantillas con el lexer de
  Django y falla si encuentra texto visible fuera de las etiquetas de
  traducción. También exige que el catálogo inglés esté 100 % traducido.

### Flujo de trabajo de traducciones

```bash
# Con GNU gettext instalado (Linux / Docker):
python manage.py makemessages -l en
# Editar locale/en/LC_MESSAGES/django.po y luego compilar (funciona también en Windows):
pip install polib && python scripts/compilar_traducciones.py
```
