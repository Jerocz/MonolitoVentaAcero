"""Internacionalizacion (gettext). Los catalogos viven en /locale."""
from django.utils.translation import gettext_lazy as _

LANGUAGE_CODE = "es"
LANGUAGES = [
    ("es", _("Español")),
    ("en", _("Inglés")),
]
USE_I18N = True

TIME_ZONE = "America/Bogota"
USE_TZ = True
