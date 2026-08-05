"""Service Layer: orquesta el flujo Cotizacion -> anticipo -> Orden de Fabricacion."""
from datetime import date, timedelta

from django.db import transaction

from ventas.domain.builders import CotizacionBuilder
from ventas.domain.excepciones import PagoRechazadoError
from ventas.infra.factories import PasarelaPagoFactory
from ventas.models import Cliente, Cotizacion, OrdenFabricacion, Pago, Producto

DIAS_FABRICACION = 20


class CotizacionService:
    def __init__(self, pasarela=None):
        # Inyeccion de dependencias: si no se pasa una pasarela, la crea la Factory.
        self.pasarela = pasarela or PasarelaPagoFactory.crear()

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

        anticipo = cotizacion.anticipo_50()
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

    @transaction.atomic
    def pagar_saldo(self, orden_id):
        orden = OrdenFabricacion.objects.get(pk=orden_id)
        if orden.esta_pagado_saldo():
            return orden
        saldo = orden.cotizacion.total - orden.cotizacion.anticipo_50()
        resultado = self.pasarela.cobrar(saldo, orden.cotizacion.cliente.email)
        if not resultado.aprobado:
            raise PagoRechazadoError("La pasarela rechazo el saldo.")
        Pago.objects.create(orden=orden, tipo=Pago.Tipo.SALDO, monto=saldo,
                           aprobado=True, referencia=resultado.referencia)
        return orden
