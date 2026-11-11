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

Organizacion del paquete:
    base.py          AutoValidado (save() -> full_clean())
    clientes.py      Cliente
    cotizaciones.py  Cotizacion, ItemCotizacion
    procesos.py      Notificacion, ReporteVentas (resultados de Celery)
"""
from ventas.models.clientes import Cliente
from ventas.models.cotizaciones import Cotizacion, ItemCotizacion
from ventas.models.procesos import Notificacion, ReporteVentas

__all__ = ["Cliente", "Cotizacion", "ItemCotizacion", "Notificacion", "ReporteVentas"]
