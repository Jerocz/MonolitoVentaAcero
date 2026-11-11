from django.db import models
from django.utils.translation import gettext_lazy as _

from ventas.models.base import AutoValidado


class Cliente(AutoValidado):
    class Tipo(models.TextChoices):
        RESTAURANTE = "RESTAURANTE", _("Restaurante")
        HOTEL = "HOTEL", _("Hotel")
        PERSONA = "PERSONA", _("Persona natural")

    nombre = models.CharField(_("nombre"), max_length=120)
    nit_o_cedula = models.CharField(_("NIT o cédula"), max_length=30)
    tipo = models.CharField(_("tipo"), max_length=12, choices=Tipo.choices, default=Tipo.PERSONA)
    email = models.EmailField(_("correo electrónico"))
    telefono = models.CharField(_("teléfono"), max_length=20, blank=True)

    class Meta:
        verbose_name = _("cliente")
        verbose_name_plural = _("clientes")

    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_display()})"
