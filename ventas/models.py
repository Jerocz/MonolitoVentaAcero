"""Modelos del dominio: Cliente, Producto (con herencia), Cotizacion, Orden y Pago."""
from decimal import Decimal

from django.db import models


class Cliente(models.Model):
    class Tipo(models.TextChoices):
        RESTAURANTE = "RESTAURANTE", "Restaurante"
        HOTEL = "HOTEL", "Hotel"
        PERSONA = "PERSONA", "Persona natural"

    nombre = models.CharField(max_length=120)
    nit_o_cedula = models.CharField(max_length=30)
    tipo = models.CharField(max_length=12, choices=Tipo.choices, default=Tipo.PERSONA)
    email = models.EmailField()
    telefono = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_display()})"


class ProductoAMedida:
    """Interfaz (mixin) para productos que se cortan a la medida."""
    ANCHO_MINIMO_CM = Decimal("60")

    def validar_medidas_minimas(self, ancho_cm):
        return Decimal(str(ancho_cm)) >= self.ANCHO_MINIMO_CM

    def es_a_medida(self):
        return True


class Producto(models.Model):
    """Clase base del catalogo (herencia multi-tabla)."""
    class Tipo(models.TextChoices):
        LAMINA = "LAMINA", "Lamina a la medida"
        MESON = "MESON", "Meson"
        CAMPANA = "CAMPANA", "Campana extractora"
        FREIDORA = "FREIDORA", "Freidora (estandar)"

    nombre = models.CharField(max_length=120)
    calibre_acero = models.IntegerField()
    precio_base_m2 = models.DecimalField(max_digits=12, decimal_places=2)
    stock_m2 = models.DecimalField(max_digits=10, decimal_places=2)
    tipo = models.CharField(max_length=10, choices=Tipo.choices)

    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_display()})"

    def instancia_real(self):
        """Devuelve la subclase concreta para el polimorfismo."""
        return getattr(self, self.tipo.lower(), self)

    def hay_stock_para(self, area_m2):
        return self.stock_m2 >= area_m2

    def descontar_stock(self, area_m2):
        self.stock_m2 -= area_m2
        self.save(update_fields=["stock_m2"])

    def _area_m2(self, ancho_cm, largo_cm, cantidad):
        return (Decimal(str(ancho_cm)) / 100) * (Decimal(str(largo_cm)) / 100) * cantidad

    def calcular_precio(self, ancho_cm, largo_cm, cantidad):
        area = self._area_m2(ancho_cm, largo_cm, cantidad)
        return (self.precio_base_m2 * area).quantize(Decimal("0.01"))


class Lamina(ProductoAMedida, Producto):
    def save(self, *args, **kwargs):
        self.tipo = Producto.Tipo.LAMINA
        super().save(*args, **kwargs)


class Meson(ProductoAMedida, Producto):
    FACTOR_REFUERZO = Decimal("1.15")

    def calcular_precio(self, ancho_cm, largo_cm, cantidad):
        base = super().calcular_precio(ancho_cm, largo_cm, cantidad)
        return (base * self.FACTOR_REFUERZO).quantize(Decimal("0.01"))

    def save(self, *args, **kwargs):
        self.tipo = Producto.Tipo.MESON
        super().save(*args, **kwargs)


class Campana(ProductoAMedida, Producto):
    COSTO_DUCTERIA = Decimal("180000")

    def calcular_precio(self, ancho_cm, largo_cm, cantidad):
        base = super().calcular_precio(ancho_cm, largo_cm, cantidad)
        return (base + self.COSTO_DUCTERIA * cantidad).quantize(Decimal("0.01"))

    def save(self, *args, **kwargs):
        self.tipo = Producto.Tipo.CAMPANA
        super().save(*args, **kwargs)


class Freidora(Producto):
    """Producto estandar: NO es a la medida, precio fijo por unidad."""
    def calcular_precio(self, ancho_cm, largo_cm, cantidad):
        return (self.precio_base_m2 * cantidad).quantize(Decimal("0.01"))

    def es_a_medida(self):
        return False

    def save(self, *args, **kwargs):
        self.tipo = Producto.Tipo.FREIDORA
        super().save(*args, **kwargs)


class Cotizacion(models.Model):
    class Estado(models.TextChoices):
        BORRADOR = "BORRADOR", "Borrador"
        ENVIADA = "ENVIADA", "Enviada al cliente"
        APROBADA = "APROBADA", "Aprobada"
        RECHAZADA = "RECHAZADA", "Rechazada"
        VENCIDA = "VENCIDA", "Vencida"

    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name="cotizaciones")
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_vencimiento = models.DateField()
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.BORRADOR)
    total = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    def __str__(self):
        return f"Cotizacion #{self.pk} - {self.cliente.nombre} - {self.estado}"

    def anticipo_50(self):
        return (self.total * Decimal("0.5")).quantize(Decimal("0.01"))


class ItemCotizacion(models.Model):
    cotizacion = models.ForeignKey(Cotizacion, related_name="items", on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    ancho_cm = models.DecimalField(max_digits=6, decimal_places=1)
    largo_cm = models.DecimalField(max_digits=6, decimal_places=1)
    cantidad = models.PositiveIntegerField(default=1)
    subtotal = models.DecimalField(max_digits=14, decimal_places=2)


class OrdenFabricacion(models.Model):
    class Estado(models.TextChoices):
        EN_COLA = "EN_COLA", "En cola"
        CORTE = "CORTE", "Corte"
        SOLDADURA = "SOLDADURA", "Soldadura"
        PULIDO = "PULIDO", "Pulido"
        TERMINADA = "TERMINADA", "Terminada"
        ENTREGADA = "ENTREGADA", "Entregada"

    SECUENCIA = [Estado.EN_COLA, Estado.CORTE, Estado.SOLDADURA,
                 Estado.PULIDO, Estado.TERMINADA, Estado.ENTREGADA]

    cotizacion = models.OneToOneField(Cotizacion, on_delete=models.PROTECT, related_name="orden")
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.EN_COLA)
    fecha_estimada_entrega = models.DateField()

    def __str__(self):
        return f"Orden #{self.pk} - {self.get_estado_display()}"

    def avanzar_etapa(self):
        i = self.SECUENCIA.index(self.estado)
        if i < len(self.SECUENCIA) - 1:
            self.estado = self.SECUENCIA[i + 1]
            self.save(update_fields=["estado"])

    def esta_pagado_saldo(self):
        return self.pagos.filter(tipo=Pago.Tipo.SALDO, aprobado=True).exists()


class Pago(models.Model):
    class Tipo(models.TextChoices):
        ANTICIPO = "ANTICIPO", "Anticipo (50%)"
        SALDO = "SALDO", "Saldo final"

    orden = models.ForeignKey(OrdenFabricacion, on_delete=models.CASCADE, related_name="pagos")
    tipo = models.CharField(max_length=10, choices=Tipo.choices)
    monto = models.DecimalField(max_digits=14, decimal_places=2)
    aprobado = models.BooleanField(default=False)
    referencia = models.CharField(max_length=64, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_tipo_display()} - ${self.monto} - orden #{self.orden_id}"
