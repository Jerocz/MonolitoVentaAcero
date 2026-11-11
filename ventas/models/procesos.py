"""Registros que generan los procesos en segundo plano (Celery)."""
from django.db import models
from django.utils.translation import gettext_lazy as _


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
