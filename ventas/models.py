"""
Modelos que se QUEDAN en el monolito despues del Strangler Pattern.

Migrados a microservicios (cada uno con su propia base de datos):
  - Producto, Lamina, Meson, Campana, Freidora  -> ms-catalogo
  - OrdenFabricacion                            -> ms-fabricacion
  - Pago                                        -> ms-pagos

El monolito conserva Clientes y Cotizaciones (el "pedido" que orquesta a los
demas servicios), y los registros de los procesos en segundo plano
(notificaciones y reportes generados por Celery). Entre servicios NO hay
llaves foraneas: se guardan referencias (`producto_ref`, `orden_ref`) y una
copia de los datos necesarios para mostrar la cotizacion aunque otro
servicio este caido.

Cada modelo valida su propio estado antes de guardarse (`save()` llama a
`full_clean()`), asi un dato invalido nunca llega a la base de datos.
"""
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from ventas.domain.reglas import referencia_cotizacion


class AutoValidado(models.Model):
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


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


class Notificacion(models.Model):
    """Registro de cada notificacion enviada por el worker de Celery."""
    destinatario = models.EmailField(_("destinatario"))
    asunto = models.CharField(_("asunto"), max_length=200)
    cuerpo = models.TextField(_("mensaje"))
    creada = models.DateTimeField(_("enviada"), auto_now_add=True)

    class Meta:
        ordering = ["-id"]
        verbose_name = _("notificación")
        verbose_name_plural = _("notificaciones")

    def __str__(self):
        return f"{self.destinatario}: {self.asunto}"


class ReporteVentas(models.Model):
    """Reporte CSV generado en segundo plano por Celery."""
    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", _("En cola")
        LISTO = "LISTO", _("Listo")
        ERROR = "ERROR", _("Con error")

    estado = models.CharField(_("estado"), max_length=10, choices=Estado.choices, default=Estado.PENDIENTE)
    archivo = models.FileField(_("archivo"), upload_to="reportes/", blank=True)
    filas = models.PositiveIntegerField(_("filas"), default=0)
    detalle = models.CharField(_("detalle"), max_length=255, blank=True)
    solicitado = models.DateTimeField(_("solicitado"), auto_now_add=True)
    terminado = models.DateTimeField(_("terminado"), null=True, blank=True)

    class Meta:
        ordering = ["-id"]
        verbose_name = _("reporte de ventas")
        verbose_name_plural = _("reportes de ventas")

    def __str__(self):
        return f"#{self.pk} {self.get_estado_display()}"
