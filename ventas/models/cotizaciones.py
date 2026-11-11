from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from ventas.domain.reglas import referencia_cotizacion
from ventas.models.base import AutoValidado
from ventas.models.clientes import Cliente


class Cotizacion(AutoValidado):
    class Estado(models.TextChoices):
        BORRADOR = "BORRADOR", _("Borrador")
        ENVIADA = "ENVIADA", _("Enviada al cliente")
        APROBADA = "APROBADA", _("Aprobada")
        RECHAZADA = "RECHAZADA", _("Rechazada")
        VENCIDA = "VENCIDA", _("Vencida")

    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name="cotizaciones",
                                verbose_name=_("cliente"))
    fecha_creacion = models.DateTimeField(_("fecha de creación"), auto_now_add=True)
    fecha_vencimiento = models.DateField(_("fecha de vencimiento"))
    estado = models.CharField(_("estado"), max_length=10, choices=Estado.choices, default=Estado.BORRADOR)
    total = models.DecimalField(
        _("total"), max_digits=14, decimal_places=2, default=0,
        validators=[MinValueValidator(Decimal("0"))])
    anticipo = models.DecimalField(
        _("anticipo cobrado"), max_digits=14, decimal_places=2, default=0,
        validators=[MinValueValidator(Decimal("0"))])
    # Id de la orden en ms-fabricacion (sin FK: vive en otra base de datos).
    orden_ref = models.PositiveIntegerField(_("orden de fabricación"), null=True, blank=True)

    class Meta:
        verbose_name = _("cotización")
        verbose_name_plural = _("cotizaciones")

    @property
    def referencia(self) -> str:
        return referencia_cotizacion(self.pk)

    def __str__(self):
        return f"{self.referencia} - {self.cliente.nombre} - {self.get_estado_display()}"


class ItemCotizacion(AutoValidado):
    cotizacion = models.ForeignKey(Cotizacion, related_name="items", on_delete=models.CASCADE)
    # Copia de los datos del producto (ms-catalogo es el duenio del producto).
    producto_ref = models.PositiveIntegerField(_("producto"))
    producto_nombre = models.CharField(_("nombre del producto"), max_length=120)
    producto_tipo = models.CharField(_("tipo de producto"), max_length=10)
    ancho_cm = models.DecimalField(
        _("ancho (cm)"), max_digits=6, decimal_places=1, validators=[MinValueValidator(Decimal("0.1"))])
    largo_cm = models.DecimalField(
        _("largo (cm)"), max_digits=6, decimal_places=1, validators=[MinValueValidator(Decimal("0.1"))])
    cantidad = models.PositiveIntegerField(_("cantidad"), default=1, validators=[MinValueValidator(1)])
    subtotal = models.DecimalField(
        _("subtotal"), max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])

    class Meta:
        verbose_name = _("ítem de cotización")
        verbose_name_plural = _("ítems de cotización")
