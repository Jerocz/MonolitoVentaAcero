# Justificación de la Estructura de Carpetas

```
monolito_venta_acero/     settings, urls, wsgi/asgi (configuración del proyecto Django)
ventas/
  models.py                Entidades (Cliente, Producto, Cotizacion, Orden, Pago...)
  domain/                  Reglas de negocio puras, sin Django ni HTTP
    builders.py               Patron Builder: CotizacionBuilder
    precios.py                Patron Strategy: EstrategiaPrecio por tipo de producto
    reglas.py                 Constantes de negocio (dias, fraccion de anticipo...)
    excepciones.py            Excepciones propias del dominio
  infra/                    Adaptadores a sistemas externos, intercambiables
    pasarelas.py               PasarelaPago (interfaz) + PasarelaReal/PasarelaMock
    factories.py                Patron Factory: PasarelaPagoFactory
  services.py               Service Layer: orquesta domain + infra + transacciones
  api.py                     Presentacion DRF (APIView)
  serializers.py              Contratos de entrada/salida de la API
  views.py                    Presentacion HTML (para la sustentacion)
  templates/, static/         Assets de las vistas HTML
  tests.py                    Pruebas automatizadas
  migrations/                  Evolucion del esquema
```

## Por qué esta separación y no "todo en `models.py` y `views.py`"

El objetivo de la entrega es demostrar **desacoplamiento total** entre la
lógica de negocio y el framework. La forma más directa de demostrarlo es
que cada carpeta tenga **una sola razón para cambiar** (SRP) y que las
dependencias apunten siempre "hacia adentro" (hacia el dominio), nunca al
revés:

- **`domain/` no importa nada de `rest_framework`, `views` ni HTTP.**
  Es Python puro (más el ORM de los modelos). Esto es deliberado: las
  reglas de negocio (cómo se cobra un mesón, cuándo un pedido es
  inválido) no deberían cambiar si mañana cambiamos DRF por otro
  framework, o si agregamos una API en GraphQL además de la REST. Es la
  capa que un profesor de arquitectura espera poder leer sin saber nada
  de Django.

- **`infra/` es la única carpeta que sabe que existe "el mundo exterior".**
  Las pasarelas de pago son el ejemplo obvio: hoy hay una `PasarelaMock`
  y una `PasarelaReal`, mañana podría haber una `PasarelaWompi` o
  `PasarelaPayU`. `infra/` aísla ese cambio para que **nadie más en el
  proyecto tenga que tocarse** cuando cambie el proveedor. El patrón
  Factory (`PasarelaPagoFactory`) vive aquí porque su trabajo es
  justamente decidir *qué adaptador externo* usar.

- **`services.py` es el único lugar que conoce tanto `domain/` como
  `infra/`, y el único que abre transacciones (`@transaction.atomic`).**
  Es la capa de aplicación: no tiene reglas de negocio propias (esas
  están en `domain/`), solo orquesta el orden de los pasos
  (`construir → cobrar → aprobar → generar orden`). Separarla de
  `domain/` importa porque la orquestación *sí* depende de infraestructura
  (necesita saber que hay una base de datos y una pasarela), mientras que
  las reglas de negocio puras no deberían depender de eso.

- **`api.py`, `serializers.py` y `views.py` son intercambiables entre sí.**
  Ambas exponen exactamente los mismos flujos de negocio (`crear_cotizacion`,
  `avanzar_etapa`, `pagar_saldo`) llamando a los mismos servicios. Esto es
  la prueba de que la lógica no vive en la capa de presentación: se puede
  apagar `views.py` (las vistas HTML de la sustentación) sin que la API
  REST pierda una sola regla de negocio, porque ninguna vive ahí.

- **`models.py` queda deliberadamente "delgado" pero no vacío.** No tiene
  orquestación de negocio (eso rompería SRP: una entidad no debería saber
  cobrar un anticipo), pero sí valida su propia integridad
  (`save()` llama `full_clean()`, ver la sección de validación en la
  [Home](Home.md)). Esa es la línea que trazamos entre "dato" (vive en el
  modelo) y "proceso de negocio" (vive en `domain/`/`services.py`).

## Resultado

Cualquier capa se puede reemplazar sin tocar las demás:

- Cambiar de SQLite a Postgres → solo `settings.py`.
- Cambiar la pasarela de pago → solo `infra/`.
- Agregar una nueva regla de precio → solo `domain/precios.py` (Strategy,
  Open/Closed).
- Exponer la misma lógica por gRPC además de REST → una carpeta nueva de
  presentación al lado de `api.py`, sin tocar `services.py` ni `domain/`.
