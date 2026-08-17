# Diagrama de Secuencia — Crear Cotización

Este es el flujo más complejo del sistema: atraviesa las cuatro capas,
usa los dos patrones creacionales obligatorios (Builder y Factory), aplica
el patrón Strategy para el precio, corre dentro de una transacción
atómica y termina cobrando un anticipo a través de una pasarela de pago.

`POST /api/cotizaciones/` → `CrearCotizacionAPIView` → `CotizacionService`
→ `CotizacionBuilder` → `PasarelaPagoFactory` → `PasarelaPago`.

## Camino feliz (201 Created)

```mermaid
sequenceDiagram
    actor Cliente as Cliente HTTP
    participant View as CrearCotizacionAPIView
    participant Ser as CrearCotizacionEntradaSerializer
    participant Svc as CotizacionService
    participant Fact as PasarelaPagoFactory
    participant Pas as PasarelaPago (Mock/Real)
    participant Build as CotizacionBuilder
    participant Estr as EstrategiaPrecio
    participant DB as Modelos (ORM)

    Cliente->>View: POST /api/cotizaciones/ {cliente_id, items[]}
    View->>Ser: is_valid(request.data)
    Ser-->>View: OK (validated_data)

    View->>Svc: crear_cotizacion(cliente_id, items)
    Svc->>Fact: crear()
    Fact-->>Svc: PasarelaMock() | PasarelaReal()  (segun ENV_TYPE)

    Svc->>DB: Cliente.objects.get(pk=cliente_id)
    DB-->>Svc: cliente

    Svc->>Build: para_cliente(cliente).con_item(...) x N
    Svc->>Build: build()
    activate Build
    Build->>Build: _validar() -- ancho minimo, stock, cliente/items presentes
    Build->>DB: Cotizacion.objects.create(cliente, fecha_vencimiento)
    DB->>DB: save() -> full_clean() (valida tipos/rangos del modelo)
    loop por cada item
        Build->>Estr: calcular(precio_base_m2, ancho, largo, cantidad)
        Estr-->>Build: subtotal
        Build->>DB: ItemCotizacion.objects.create(...)
        DB->>DB: save() -> full_clean()
        Build->>DB: producto.stock_m2 -= area; producto.save()
        DB->>DB: save() -> full_clean()
    end
    Build->>DB: cotizacion.total = suma; cotizacion.save()
    deactivate Build
    Build-->>Svc: cotizacion

    Svc->>DB: cotizacion.estado = ENVIADA; save()
    Svc->>Svc: anticipo = calcular_anticipo(total)
    Svc->>Pas: cobrar(anticipo, cliente.email)
    Pas-->>Svc: ResultadoPago(aprobado=True, referencia)

    Svc->>DB: cotizacion.estado = APROBADA; save()
    Svc->>DB: OrdenFabricacion.objects.create(cotizacion, fecha_estimada_entrega)
    Svc->>DB: Pago.objects.create(orden, ANTICIPO, monto, referencia)
    Svc-->>View: cotizacion (con .orden)

    View->>View: CotizacionSalidaSerializer(cotizacion)
    View-->>Cliente: 201 Created {id, estado: APROBADA, total, orden{...}}
```

## Caminos de error (por qué cada código HTTP)

```mermaid
sequenceDiagram
    actor Cliente as Cliente HTTP
    participant View as CrearCotizacionAPIView
    participant Svc as CotizacionService
    participant Build as CotizacionBuilder
    participant Pas as PasarelaPago

    alt payload mal formado
        Cliente->>View: POST sin "items" o con tipos invalidos
        View->>View: Serializer.is_valid() == False
        View-->>Cliente: 400 Bad Request {errors}
    else cliente o producto no existe
        Cliente->>View: POST cliente_id=9999
        View->>Svc: crear_cotizacion(...)
        Svc-->>View: raise Cliente.DoesNotExist
        View-->>Cliente: 404 Not Found
    else regla de negocio violada (ancho < 60cm, sin stock, o full_clean() del modelo falla)
        Cliente->>View: POST ancho_cm=30
        View->>Svc: crear_cotizacion(...)
        Svc->>Build: build()
        Build->>Build: _validar() falla -> PedidoInvalidoError
        Note over Build: o: full_clean() del modelo lanza<br/>ValidationError -> se traduce a<br/>PedidoInvalidoError (mensaje_de())
        Build-->>Svc: raise PedidoInvalidoError
        Svc-->>View: propaga PedidoInvalidoError
        View-->>Cliente: 409 Conflict {error}
    else la pasarela rechaza el anticipo
        Cliente->>View: POST (normal)
        View->>Svc: crear_cotizacion(...)
        Svc->>Pas: cobrar(anticipo, email)
        Pas-->>Svc: ResultadoPago(aprobado=False)
        Svc->>Svc: cotizacion.estado = RECHAZADA; raise PagoRechazadoError
        Note over Svc: @transaction.atomic revierte<br/>TODO (cotizacion, items, stock, orden)
        Svc-->>View: raise PagoRechazadoError
        View-->>Cliente: 409 Conflict {error}
    end
```

## Puntos que vale la pena explicar en la sustentación

1. **Dos niveles de validación, dos responsabilidades distintas.**
   `CotizacionBuilder._validar()` valida **reglas de negocio** que
   requieren conocer más de una entidad (¿hay stock suficiente para
   *este* producto? ¿el ancho pedido cumple el mínimo de *esa*
   estrategia de precio?). `Model.save() → full_clean()` valida
   **invariantes de la entidad misma** (¿el monto es positivo? ¿el
   calibre es 304 o 430? ¿la cantidad es al menos 1?), sin importar si el
   objeto lo crea el Builder, el admin de Django o una prueba. Por eso el
   Builder atrapa `django.core.exceptions.ValidationError` y lo traduce a
   `PedidoInvalidoError`: la capa de presentación (`api.py`) nunca ve un
   tipo de excepción que pertenezca al framework, solo excepciones de
   dominio.

2. **Transacción atómica**: todo el bloque de `crear_cotizacion` corre en
   `@transaction.atomic`. Si la pasarela rechaza el anticipo *después* de
   haber descontado stock y creado la cotización, Django revierte todo: no
   queda stock fantasma descontado ni una cotización "aprobada a medias".

3. **Inyección de dependencias vía Factory**: `CotizacionService` no
   decide qué pasarela usar; se la inyecta `PasarelaPagoFactory.crear()`
   en el constructor (o una pasarela de prueba, como hacen los tests). Es
   lo que permite probar el flujo completo sin llamar a un proveedor de
   pagos real (`PasarelaAprueba`/`PasarelaRechaza` en `tests.py`).
