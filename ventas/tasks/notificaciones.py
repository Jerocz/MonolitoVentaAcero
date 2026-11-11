"""Notificaciones al cliente (correo + registro en la tabla Notificacion)."""
from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.utils import translation
from django.utils.translation import gettext as _

from ventas.domain.reglas import id_desde_referencia
from ventas.models import Cotizacion, Notificacion


def _enviar(destinatario, asunto, cuerpo):
    send_mail(asunto, cuerpo, settings.DEFAULT_FROM_EMAIL, [destinatario], fail_silently=True)
    Notificacion.objects.create(destinatario=destinatario, asunto=asunto, cuerpo=cuerpo)


@shared_task
def notificar_cotizacion_aprobada(cotizacion_id, idioma=None):
    with translation.override(idioma or settings.LANGUAGE_CODE):
        cot = Cotizacion.objects.select_related("cliente").get(pk=cotizacion_id)
        asunto = _("Tu cotización %(ref)s fue aprobada") % {"ref": cot.referencia}
        cuerpo = _(
            "Hola %(cliente)s:\n\nRecibimos el anticipo de $%(anticipo)s para la cotización %(ref)s "
            "(total $%(total)s). Tu pedido ya entró a la fila de fabricación.\n\n%(empresa)s"
        ) % {"cliente": cot.cliente.nombre, "anticipo": f"{cot.anticipo:,.0f}", "ref": cot.referencia,
             "total": f"{cot.total:,.0f}", "empresa": settings.EMPRESA["NOMBRE"]}
        _enviar(cot.cliente.email, asunto, cuerpo)


@shared_task
def notificar_cambio_etapa(cotizacion_ref, estado_display, idioma=None):
    with translation.override(idioma or settings.LANGUAGE_CODE):
        cot = Cotizacion.objects.select_related("cliente").filter(pk=id_desde_referencia(cotizacion_ref)).first()
        if cot is None:
            return
        asunto = _("Tu pedido %(ref)s avanzó a: %(etapa)s") % {"ref": cotizacion_ref, "etapa": estado_display}
        cuerpo = _("Hola %(cliente)s:\n\nTu pedido %(ref)s ahora está en la etapa \"%(etapa)s\".\n\n%(empresa)s") % {
            "cliente": cot.cliente.nombre, "ref": cotizacion_ref, "etapa": estado_display,
            "empresa": settings.EMPRESA["NOMBRE"]}
        _enviar(cot.cliente.email, asunto, cuerpo)
