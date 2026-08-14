"""Service Layer: orquesta el negocio. Aqui vive la logica que antes estaba
en los modelos (calculo de anticipo, avance de estados, saldo)."""
from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction

from ventas.domain.builders import CotizacionBuilder
from ventas.domain.excepciones import PagoRechazadoError
from ventas.domain.reglas import DIAS_FABRICACION, FRACCION_ANTICIPO, SECUENCIA_ETAPAS
from ventas.infra.factories import PasarelaPagoFactory
from ventas.models import Cliente, Cotizacion, OrdenFabricacion, Pago, Producto


class CotizacionService:
    def __init__(self, pasarela=None):
        self.pasarela = pasarela or PasarelaPagoFactory.crear()

    @staticmethod
    def calcular_anticipo(total: Decimal) -> Decimal:
        return (total * FRACCION_ANTICIPO).quantize(Decimal("0.01"))

    @transaction.atomic
    def crear_cotizacion(self, cliente_id, items):
        cliente = Cliente.objects.get(pk=cliente_id)

        builder = CotizacionBuilder().para_cliente(cliente)
        for item in items:
            producto = Producto.objects.get(pk=item["producto_id"])
            builder.con_item(producto, ancho_cm=item["ancho_cm"],
                             largo_cm=item["largo_cm"], cantidad=item.get("cantidad", 1))
        cotizacion = builder.build()

        cotizacion.estado = Cotizacion.Estado.ENVIADA
        cotizacion.save(update_fields=["estado"])

        anticipo = self.calcular_anticipo(cotizacion.total)
        resultado = self.pasarela.cobrar(anticipo, cliente.email)

        if not resultado.aprobado:
            cotizacion.estado = Cotizacion.Estado.RECHAZADA
            cotizacion.save(update_fields=["estado"])
            raise PagoRechazadoError("La pasarela rechazo el anticipo.")

        cotizacion.estado = Cotizacion.Estado.APROBADA
        cotizacion.save(update_fields=["estado"])
        orden = OrdenFabricacion.objects.create(
            cotizacion=cotizacion,
            fecha_estimada_entrega=date.today() + timedelta(days=DIAS_FABRICACION))
        Pago.objects.create(orden=orden, tipo=Pago.Tipo.ANTICIPO, monto=anticipo,
                           aprobado=True, referencia=resultado.referencia)
        return cotizacion


class OrdenService:
    """Logica de la orden de fabricacion (estados y saldo)."""

    def __init__(self, pasarela=None):
        self.pasarela = pasarela or PasarelaPagoFactory.crear()

    def avanzar_etapa(self, orden_id) -> OrdenFabricacion:
        orden = OrdenFabricacion.objects.get(pk=orden_id)
        i = SECUENCIA_ETAPAS.index(orden.estado)
        if i < len(SECUENCIA_ETAPAS) - 1:
            orden.estado = SECUENCIA_ETAPAS[i + 1]
            orden.save(update_fields=["estado"])
        return orden

    def saldo_pagado(self, orden) -> bool:
        return orden.pagos.filter(tipo=Pago.Tipo.SALDO, aprobado=True).exists()

    @transaction.atomic
    def pagar_saldo(self, orden_id) -> OrdenFabricacion:
        orden = OrdenFabricacion.objects.get(pk=orden_id)
        if self.saldo_pagado(orden):
            return orden
        anticipo = CotizacionService.calcular_anticipo(orden.cotizacion.total)
        saldo = orden.cotizacion.total - anticipo
        resultado = self.pasarela.cobrar(saldo, orden.cotizacion.cliente.email)
        if not resultado.aprobado:
            raise PagoRechazadoError("La pasarela rechazo el saldo.")
        Pago.objects.create(orden=orden, tipo=Pago.Tipo.SALDO, monto=saldo,
                           aprobado=True, referencia=resultado.referencia)
        return orden
