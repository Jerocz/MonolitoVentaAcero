"""Service Layer del monolito: orquesta a los microservicios.

`CotizacionService.crear_cotizacion` es una SAGA orquestada:

  1. Monolito      crea la cotizacion (BORRADOR)
  2. ms-catalogo   valida reglas, calcula precios y RESERVA stock
  3. ms-pagos      cobra el anticipo del 50%
        - rechazado / caido -> COMPENSA: libera el stock y marca RECHAZADA
  4. ms-fabricacion abre la orden
        - caido -> no se pierde la venta: Celery reintenta crear la orden
  5. Celery        notifica al cliente (segundo plano)

Los servicios dependen solo de PUERTOS (ventas/domain/puertos.py); las
implementaciones se inyectan (por defecto desde el Contenedor).
"""
import logging
from datetime import date, timedelta

from django.db import transaction
from django.utils.translation import gettext as _

from ventas.domain.dtos import OrdenDTO
from ventas.domain.excepciones import (
    PagoRechazadoError,
    PedidoInvalidoError,
    RecursoNoEncontradoError,
    ServicioNoDisponibleError,
)
from ventas.domain.puertos import CatalogoPort, ColaTareasPort, FabricacionPort, PagosPort
from ventas.domain.reglas import DIAS_VIGENCIA_COTIZACION
from ventas.infra.contenedor import Contenedor
from ventas.models import Cliente, Cotizacion, ItemCotizacion

log = logging.getLogger(__name__)


class CotizacionService:
    def __init__(self, catalogo: CatalogoPort | None = None, pagos: PagosPort | None = None,
                 fabricacion: FabricacionPort | None = None, cola: ColaTareasPort | None = None):
        self.catalogo = catalogo or Contenedor.catalogo()
        self.pagos = pagos or Contenedor.pagos()
        self.fabricacion = fabricacion or Contenedor.fabricacion()
        self.cola = cola or Contenedor.cola_tareas()

    def crear_cotizacion(self, cliente_id, items) -> Cotizacion:
        cliente = Cliente.objects.get(pk=cliente_id)
        if not items:
            raise PedidoInvalidoError(_("La cotización debe tener al menos un ítem."))

        cotizacion = Cotizacion.objects.create(
            cliente=cliente, fecha_vencimiento=date.today() + timedelta(days=DIAS_VIGENCIA_COTIZACION))
        ref = cotizacion.referencia

        # Paso 2: precios + reglas + stock (ms-catalogo)
        try:
            reserva = self.catalogo.reservar(ref, items)
        except (PedidoInvalidoError, RecursoNoEncontradoError, ServicioNoDisponibleError):
            cotizacion.delete()  # nada que compensar: no se aparto stock
            raise

        with transaction.atomic():
            for linea in reserva.lineas:
                ItemCotizacion.objects.create(
                    cotizacion=cotizacion, producto_ref=linea.producto_id,
                    producto_nombre=linea.producto_nombre, producto_tipo=linea.producto_tipo,
                    ancho_cm=linea.ancho_cm, largo_cm=linea.largo_cm,
                    cantidad=linea.cantidad, subtotal=linea.subtotal)
            cotizacion.total = reserva.total
            cotizacion.estado = Cotizacion.Estado.ENVIADA
            cotizacion.save(update_fields=["total", "estado"])

        # Paso 3: anticipo (ms-pagos)
        try:
            cobro = self.pagos.cobrar_anticipo(ref, cotizacion.total, cliente.email)
        except ServicioNoDisponibleError:
            self._compensar(cotizacion)
            raise
        if not cobro.aprobado:
            self._compensar(cotizacion)
            raise PagoRechazadoError(_("La pasarela rechazó el anticipo."))

        cotizacion.estado = Cotizacion.Estado.APROBADA
        cotizacion.anticipo = cobro.monto
        cotizacion.save(update_fields=["estado", "anticipo"])

        # Paso 4: orden de fabricacion (ms-fabricacion)
        try:
            orden = self.fabricacion.crear_orden(ref, cliente.nombre, cotizacion.total)
            cotizacion.orden_ref = orden.id
            cotizacion.save(update_fields=["orden_ref"])
        except ServicioNoDisponibleError:
            log.warning("ms-fabricacion no disponible; la orden de %s se creara en segundo plano", ref)
            self.cola.programar_creacion_orden(cotizacion.id)

        # Paso 5: notificacion asincrona
        self.cola.notificar_cotizacion_aprobada(cotizacion.id)
        return cotizacion

    def _compensar(self, cotizacion: Cotizacion):
        """Transaccion compensatoria de la saga: devuelve el stock reservado."""
        try:
            self.catalogo.liberar(cotizacion.referencia)
        except ServicioNoDisponibleError:
            log.error("No se pudo liberar el stock de %s; requiere revision manual", cotizacion.referencia)
        cotizacion.estado = Cotizacion.Estado.RECHAZADA
        cotizacion.save(update_fields=["estado"])

    def crear_orden_pendiente(self, cotizacion_id) -> OrdenDTO | None:
        """Usado por Celery cuando ms-fabricacion estaba caido (idempotente)."""
        cotizacion = Cotizacion.objects.select_related("cliente").get(pk=cotizacion_id)
        if cotizacion.orden_ref or cotizacion.estado != Cotizacion.Estado.APROBADA:
            return None
        orden = self.fabricacion.crear_orden(cotizacion.referencia, cotizacion.cliente.nombre, cotizacion.total)
        cotizacion.orden_ref = orden.id
        cotizacion.save(update_fields=["orden_ref"])
        return orden
