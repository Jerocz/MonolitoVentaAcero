"""Dobles de prueba (fakes en memoria) para cada puerto del dominio.

Gracias a la inversion de dependencias, las pruebas del monolito no
necesitan levantar los microservicios ni tener red.
"""
from dataclasses import replace
from datetime import date, datetime, timezone
from decimal import Decimal

from django.test import TestCase

from ventas.domain.dtos import (
    CobroDTO,
    EstadoPagoDTO,
    InfoAliadoDTO,
    LineaReservadaDTO,
    OrdenDTO,
    ProductoDTO,
    ReservaDTO,
    TasaCambioDTO,
)
from ventas.domain.excepciones import (
    OperacionNoPermitidaError,
    PedidoInvalidoError,
    RecursoNoEncontradoError,
    ServicioNoDisponibleError,
)
from ventas.domain.puertos import (
    CatalogoPort,
    ColaTareasPort,
    FabricacionPort,
    PagosPort,
    ServicioAliadoPort,
    TasaCambioPort,
)
from ventas.infra.contenedor import Contenedor

ETAPAS = ["EN_COLA", "CORTE", "SOLDADURA", "PULIDO", "TERMINADA", "ENTREGADA"]


def producto(id, nombre="Lamina", tipo="LAMINA", precio="100000", stock="100", a_medida=True):
    return ProductoDTO(id=id, nombre=nombre, tipo=tipo, tipo_display=tipo.title(), calibre_acero=304,
                       precio_base_m2=Decimal(precio), stock_m2=Decimal(stock), es_a_medida=a_medida,
                       unidad="m2" if a_medida else "unidad",
                       ancho_minimo_cm=Decimal("60") if a_medida else None)


class FakeCatalogo(CatalogoPort):
    def __init__(self, productos=None, caido=False):
        self.productos = {p.id: p for p in (productos or [producto(1)])}
        self.caido = caido
        self.reservas: dict[str, ReservaDTO] = {}
        self.liberadas: list[str] = []

    def _revisar(self):
        if self.caido:
            raise ServicioNoDisponibleError("ms-catalogo", "fake caido")

    def listar_productos(self):
        self._revisar()
        return list(self.productos.values())

    def reservar(self, referencia, items):
        self._revisar()
        lineas = []
        for i in items:
            p = self.productos.get(int(i["producto_id"]))
            if p is None:
                raise RecursoNoEncontradoError("El producto no existe.")
            ancho, largo, cant = Decimal(str(i["ancho_cm"])), Decimal(str(i["largo_cm"])), int(i.get("cantidad", 1))
            if p.es_a_medida and ancho < 60:
                raise PedidoInvalidoError(f"'{p.nombre}': el ancho mínimo es 60 cm.")
            subtotal = (p.precio_base_m2 * ancho / 100 * largo / 100 * cant).quantize(Decimal("0.01"))
            lineas.append(LineaReservadaDTO(p.id, p.nombre, p.tipo, ancho, largo, cant, subtotal))
        reserva = ReservaDTO(referencia, sum((l.subtotal for l in lineas), Decimal("0")), lineas)
        self.reservas[referencia] = reserva
        return reserva

    def liberar(self, referencia):
        self._revisar()
        self.liberadas.append(referencia)


class FakePagos(PagosPort):
    def __init__(self, aprueba=True, caido=False):
        self.aprueba, self.caido = aprueba, caido
        self.cobros: list[tuple[str, str, Decimal]] = []

    def _cobrar(self, tipo, ref, monto):
        if self.caido:
            raise ServicioNoDisponibleError("ms-pagos", "fake caido")
        if tipo == "SALDO" and not any(c[0] == "ANTICIPO" and c[1] == ref for c in self.cobros):
            raise OperacionNoPermitidaError("sin anticipo")
        if self.aprueba:
            self.cobros.append((tipo, ref, monto))
        return CobroDTO(aprobado=self.aprueba, monto=monto, referencia=f"FAKE-{len(self.cobros)}")

    def cobrar_anticipo(self, referencia, total, email):
        return self._cobrar("ANTICIPO", referencia, (Decimal(total) / 2).quantize(Decimal("0.01")))

    def cobrar_saldo(self, referencia, total, email):
        return self._cobrar("SALDO", referencia, Decimal(total) - (Decimal(total) / 2).quantize(Decimal("0.01")))

    def estado(self, referencias):
        if self.caido:
            raise ServicioNoDisponibleError("ms-pagos", "fake caido")
        return {r: EstadoPagoDTO(anticipo_pagado=any(c[:2] == ("ANTICIPO", r) for c in self.cobros),
                                 saldo_pagado=any(c[:2] == ("SALDO", r) for c in self.cobros))
                for r in referencias}


class FakeFabricacion(FabricacionPort):
    def __init__(self, caido=False):
        self.caido = caido
        self.ordenes: dict[int, OrdenDTO] = {}

    def _revisar(self):
        if self.caido:
            raise ServicioNoDisponibleError("ms-fabricacion", "fake caido")

    def crear_orden(self, referencia, cliente, total):
        self._revisar()
        for o in self.ordenes.values():
            if o.cotizacion_ref == referencia:
                return o
        orden = OrdenDTO(len(self.ordenes) + 1, referencia, cliente, Decimal(total), "EN_COLA",
                         "En cola", 0, 0, date(2026, 12, 1))
        self.ordenes[orden.id] = orden
        return orden

    def listar_ordenes(self, limite=8):
        self._revisar()
        return sorted(self.ordenes.values(), key=lambda o: -o.id)[:limite]

    def obtener(self, orden_id):
        self._revisar()
        if orden_id not in self.ordenes:
            raise RecursoNoEncontradoError("La orden no existe.")
        return self.ordenes[orden_id]

    def avanzar(self, orden_id):
        orden = self.obtener(orden_id)
        if orden.indice_etapa == len(ETAPAS) - 1:
            raise OperacionNoPermitidaError("La orden ya fue entregada.")
        i = orden.indice_etapa + 1
        self.ordenes[orden_id] = replace(orden, estado=ETAPAS[i], estado_display=ETAPAS[i].title(),
                                         indice_etapa=i, progreso=i * 20)
        return self.ordenes[orden_id]

    def etapas(self):
        self._revisar()
        return list(ETAPAS)


class FakeCola(ColaTareasPort):
    def __init__(self):
        self.llamadas: list[tuple] = []

    def notificar_cotizacion_aprobada(self, cotizacion_id):
        self.llamadas.append(("cotizacion_aprobada", cotizacion_id))

    def notificar_cambio_etapa(self, cotizacion_ref, estado_display):
        self.llamadas.append(("cambio_etapa", cotizacion_ref))

    def programar_creacion_orden(self, cotizacion_id):
        self.llamadas.append(("crear_orden", cotizacion_id))

    def generar_reporte(self, reporte_id):
        self.llamadas.append(("reporte", reporte_id))

    def nombres(self):
        return [l[0] for l in self.llamadas]


class FakeTasa(TasaCambioPort):
    def obtener(self, origen="COP", destino="USD"):
        return TasaCambioDTO(origen, destino, Decimal("0.00025"), "fake",
                             datetime(2026, 11, 10, tzinfo=timezone.utc))


class FakeAliado(ServicioAliadoPort):
    def consultar(self):
        return InfoAliadoDTO(nombre="Equipo aliado", disponible=True, url="http://aliado.test",
                             elementos=[{"servicio": "Envios", "precio": 1000}])


class ConDobles(TestCase):
    """Base: inyecta dobles en el Contenedor antes de cada prueba."""

    def setUp(self):
        super().setUp()
        self.catalogo = FakeCatalogo([producto(1), producto(2, "Freidora", "FREIDORA", "2000000", "10", False)])
        self.pagos = FakePagos()
        self.fabricacion = FakeFabricacion()
        self.cola = FakeCola()
        Contenedor.sobrescribir(catalogo=self.catalogo, pagos=self.pagos, fabricacion=self.fabricacion,
                                cola_tareas=self.cola, tasa_cambio=FakeTasa(), aliado=FakeAliado())
        self.addCleanup(Contenedor.restablecer)
