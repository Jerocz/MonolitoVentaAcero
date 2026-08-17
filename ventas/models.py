"""
Modelos de dominio: datos, relaciones, persistencia y las validaciones de
integridad propias de cada entidad (tipos, rangos, invariantes). La logica
de negocio orquestada entre varias entidades (precios, stock cruzado,
anticipos, estados) vive en la capa de servicios y en las estrategias de
precio, no aqui.

Cada modelo valida su propio estado antes de guardarse (`save()` llama a
`full_clean()`), asi que un dato invalido nunca llega a la base de datos
sin importar por que camino se creo el objeto (builder, admin, shell). El
Builder y el Service Layer, mas arriba, atrapan `ValidationError` de Django
y la traducen a `PedidoInvalidoError` para no filtrar un tipo de excepcion
de framework hacia la capa de presentacion.
"""
from decimal import Decimal

from django.core.validators import MinValueValidator
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

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_display()})"


class Producto(models.Model):
    """Base del catalogo. Las subclases solo declaran su tipo."""
    class Tipo(models.TextChoices):
        LAMINA = "LAMINA", "Lamina a la medida"
        MESON = "MESON", "Meson"
        CAMPANA = "CAMPANA", "Campana extractora"
        FREIDORA = "FREIDORA", "Freidora (estandar)"

    class Calibre(models.IntegerChoices):
        C304 = 304, "304"
        C430 = 430, "430"

    nombre = models.CharField(max_length=120)
    calibre_acero = models.IntegerField(choices=Calibre.choices)
    precio_base_m2 = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))])
    stock_m2 = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))])
    tipo = models.CharField(max_length=10, choices=Tipo.choices)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_display()})"


class Lamina(Producto):
    def save(self, *args, **kwargs):
        self.tipo = Producto.Tipo.LAMINA
        super().save(*args, **kwargs)


class Meson(Producto):
    def save(self, *args, **kwargs):
        self.tipo = Producto.Tipo.MESON
        super().save(*args, **kwargs)


class Campana(Producto):
    def save(self, *args, **kwargs):
        self.tipo = Producto.Tipo.CAMPANA
        super().save(*args, **kwargs)


class Freidora(Producto):
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
    total = models.DecimalField(
        max_digits=14, decimal_places=2, default=0,
        validators=[MinValueValidator(Decimal("0"))])

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Cotizacion #{self.pk} - {self.cliente.nombre} - {self.estado}"


class ItemCotizacion(models.Model):
    cotizacion = models.ForeignKey(Cotizacion, related_name="items", on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    ancho_cm = models.DecimalField(
        max_digits=6, decimal_places=1,
        validators=[MinValueValidator(Decimal("0.1"))])
    largo_cm = models.DecimalField(
        max_digits=6, decimal_places=1,
        validators=[MinValueValidator(Decimal("0.1"))])
    cantidad = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    subtotal = models.DecimalField(
        max_digits=14, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))])

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class OrdenFabricacion(models.Model):
    class Estado(models.TextChoices):
        EN_COLA = "EN_COLA", "En cola"
        CORTE = "CORTE", "Corte"
        SOLDADURA = "SOLDADURA", "Soldadura"
        PULIDO = "PULIDO", "Pulido"
        TERMINADA = "TERMINADA", "Terminada"
        ENTREGADA = "ENTREGADA", "Entregada"

    cotizacion = models.OneToOneField(Cotizacion, on_delete=models.PROTECT, related_name="orden")
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.EN_COLA)
    fecha_estimada_entrega = models.DateField()

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Orden #{self.pk} - {self.get_estado_display()}"


class Pago(models.Model):
    class Tipo(models.TextChoices):
        ANTICIPO = "ANTICIPO", "Anticipo (50%)"
        SALDO = "SALDO", "Saldo final"

    orden = models.ForeignKey(OrdenFabricacion, on_delete=models.CASCADE, related_name="pagos")
    tipo = models.CharField(max_length=10, choices=Tipo.choices)
    monto = models.DecimalField(
        max_digits=14, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))])
    aprobado = models.BooleanField(default=False)
    referencia = models.CharField(max_length=64, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_tipo_display()} - ${self.monto} - orden #{self.orden_id}"
