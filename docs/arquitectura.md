# Arquitectura — Entrega 2: microservicios, integración y resiliencia

> Los diagramas están en Mermaid: GitHub los dibuja directamente. Se pueden
> copiar tal cual a la Wiki del repositorio.

## 1. Vista de despliegue (AWS Academy)

```mermaid
flowchart TB
    usuario([Navegador / equipo aliado])
    subgraph AWS["AWS Academy · Región us-east-1"]
      eip[/"IP elástica"/]
      subgraph SG["Security Group: entrada 22 (SSH) y 80 (HTTP)"]
        subgraph EC2["Instancia EC2 Ubuntu · Docker Compose"]
          subgraph red_interna["red Docker: interna"]
            nginx["gateway<br/>Nginx 1.27<br/>:80"]
            web["web<br/>Django 6 + DRF<br/>Gunicorn :8000"]
            cat["ms_catalogo<br/>Flask :5000"]
            pag["ms_pagos<br/>Flask :5000"]
            fab["ms_fabricacion<br/>Flask :5000"]
          end
          subgraph red_datos["red Docker: datos"]
            pg[("PostgreSQL 16<br/>ventas · catalogo · pagos · fabricacion")]
            redis[("Redis 7<br/>broker + caché")]
            worker["worker<br/>Celery"]
            beat["beat<br/>Celery Beat"]
          end
        end
      end
    end
    ext[["API de terceros<br/>open.er-api.com"]]
    aliado[["Servicio del<br/>equipo aliado"]]

    usuario -->|HTTP :80| eip --> nginx
    nginx -->|"/ y /api/*"| web
    nginx -->|"/api/catalogo/* (GET)"| cat
    nginx -->|"/api/fabricacion/* (GET)"| fab
    nginx -->|"/api/pagos/health"| pag
    web -->|"HTTP interno (reservar, liberar)"| cat
    web -->|"HTTP interno (anticipo, saldo)"| pag
    web -->|"HTTP interno (órdenes)"| fab
    web -->|encola tareas| redis
    beat -->|tareas periódicas| redis
    redis --> worker
    worker --> pg
    web --> pg
    cat --> pg
    pag --> pg
    fab --> pg
    web -->|Adapter + caché| ext
    web -->|Adapter| aliado
```

Solo **Nginx** publica un puerto. La red `datos` aísla PostgreSQL y Redis: el
gateway no puede llegar a ellos. Cada microservicio tiene **su propia base de
datos y su propio usuario** (Database per Service), creados por
`docker/postgres/01-crear-bases.sh`.

## 2. Strangler Pattern: qué se migró

```mermaid
flowchart LR
    subgraph E1["Entrega 1: monolito Django"]
      m1[Clientes]
      m2[Cotizaciones]
      m3[Productos + Strategy de precios]
      m4[Reglas: ancho mínimo, stock]
      m5[Pasarelas de pago + Factory]
      m6[Anticipo 50 % y saldo]
      m7[Órdenes y etapas]
    end
    subgraph E2["Entrega 2"]
      d1[Django: Clientes]
      d2[Django: Cotizaciones = orquestador de la saga]
      c1[ms-catalogo]
      p1[ms-pagos]
      f1[ms-fabricacion]
    end
    m1 --> d1
    m2 --> d2
    m3 --> c1
    m4 --> c1
    m5 --> p1
    m6 --> p1
    m7 --> f1
```

| Lógica / dato | Antes (monolito) | Ahora |
|---|---|---|
| Catálogo y stock | `models.Producto` + subclases | **ms-catalogo** (`productos`) |
| Strategy de precios | `ventas/domain/precios.py` | **ms-catalogo** `app/dominio/precios.py` |
| Reglas de la cotización (Builder) | `ventas/domain/builders.py` | **ms-catalogo** `app/dominio/cotizador.py` |
| Reserva y liberación de stock | — (descontaba directo) | **ms-catalogo** `/reservas` (nuevo, con compensación) |
| Pasarelas real/mock + Factory | `ventas/infra/` | **ms-pagos** `app/infra/pasarelas.py` |
| Anticipo 50 % y saldo | `ventas/services.py` | **ms-pagos** `app/dominio/reglas.py` |
| Registro de pagos | `models.Pago` | **ms-pagos** (`cobros`) |
| Órdenes y secuencia de etapas | `models.OrdenFabricacion`, `reglas.py` | **ms-fabricacion** (`ordenes`, `eventos_orden`) |
| Clientes, cotizaciones | Django | Django (orquestador) |
| Notificaciones, reportes, vencimientos | — | Django + **Celery** (segundo plano) |

De las 7 responsabilidades de negocio que tenía el monolito, **5 viven ahora en
microservicios independientes** (≈ 71 %). Django conserva clientes y la
orquestación de la cotización, más la interfaz web.

## 3. Saga de "crear cotización" (orquestada, con compensación)

```mermaid
sequenceDiagram
    autonumber
    actor U as Usuario
    participant N as Nginx
    participant D as Django (CotizacionService)
    participant C as ms-catalogo
    participant P as ms-pagos
    participant F as ms-fabricacion
    participant R as Redis
    participant W as Worker Celery

    U->>N: POST / (formulario)
    N->>D: proxy_pass
    D->>D: CotizacionForm valida campos
    D->>D: crea Cotización BORRADOR (COT-n)
    D->>C: POST /api/catalogo/reservas {COT-n, items}
    alt regla incumplida / producto inexistente
        C-->>D: 409 / 404 (mensaje traducido)
        D->>D: borra la cotización
        D-->>U: formulario con el error
    end
    C-->>D: 201 líneas con precio + total (stock apartado)
    D->>D: guarda ítems, estado ENVIADA
    D->>P: POST /api/pagos/anticipos {COT-n, total, email}
    alt pago rechazado (402) o ms-pagos caído
        D->>C: POST /reservas/COT-n/liberar (compensación)
        D->>D: estado RECHAZADA
        D-->>U: "La pasarela rechazó el anticipo"
    end
    P-->>D: 201 anticipo aprobado
    D->>D: estado APROBADA
    D->>F: POST /api/fabricacion/ordenes {COT-n}
    alt ms-fabricacion caído
        D->>R: encola crear_orden_pendiente (reintento con backoff)
    end
    F-->>D: 201 orden #m
    D->>R: encola notificar_cotizacion_aprobada
    D-->>U: 302 → /?cotizacion=n (Post/Redirect/Get)
    R->>W: entrega la tarea
    W->>W: envía correo y registra la notificación
```

Todos los endpoints de escritura de los microservicios son **idempotentes**
por referencia (`COT-n`), por eso el cliente HTTP puede reintentar sin cobrar
dos veces ni duplicar órdenes.

## 4. Puertos y adaptadores (Inversión de Dependencias)

```mermaid
classDiagram
    direction LR
    class CotizacionService
    class OrdenService
    class CatalogoPort { <<interface>> }
    class PagosPort { <<interface>> }
    class FabricacionPort { <<interface>> }
    class TasaCambioPort { <<interface>> }
    class ServicioAliadoPort { <<interface>> }
    class ColaTareasPort { <<interface>> }
    class CatalogoHttpAdapter
    class PagosHttpAdapter
    class FabricacionHttpAdapter
    class ExchangeRateApiAdapter
    class TasaCambioFija
    class TasaCambioConRespaldo
    class AliadoHttpAdapter
    class ColaTareasCelery
    class ClienteHttp {
      timeout
      retry + backoff
      CircuitBreaker
    }
    class Contenedor { composition root }

    CotizacionService ..> CatalogoPort
    CotizacionService ..> PagosPort
    CotizacionService ..> FabricacionPort
    CotizacionService ..> ColaTareasPort
    OrdenService ..> FabricacionPort
    OrdenService ..> PagosPort
    CatalogoHttpAdapter ..|> CatalogoPort
    PagosHttpAdapter ..|> PagosPort
    FabricacionHttpAdapter ..|> FabricacionPort
    ExchangeRateApiAdapter ..|> TasaCambioPort
    TasaCambioFija ..|> TasaCambioPort
    TasaCambioConRespaldo ..|> TasaCambioPort
    TasaCambioConRespaldo o-- ExchangeRateApiAdapter : principal
    TasaCambioConRespaldo o-- TasaCambioFija : respaldo
    AliadoHttpAdapter ..|> ServicioAliadoPort
    ColaTareasCelery ..|> ColaTareasPort
    CatalogoHttpAdapter --> ClienteHttp
    PagosHttpAdapter --> ClienteHttp
    FabricacionHttpAdapter --> ClienteHttp
    ExchangeRateApiAdapter --> ClienteHttp
    Contenedor ..> CatalogoHttpAdapter : crea
    Contenedor ..> TasaCambioConRespaldo : crea
```

* **Puertos**: `ventas/domain/puertos.py` (abstracciones) y `ventas/domain/dtos.py` (datos).
* **Adaptadores**: `ventas/infra/microservicios/` (catálogo, pagos, fabricación), `ventas/infra/externos/` (tasa de cambio, aliado) y `ventas/infra/mensajeria/` (Celery).
* **Composition root**: `ventas/infra/contenedor.py`. Las pruebas inyectan dobles en memoria (`ventas/tests/dobles.py`).

### Patrón Adapter con la API de terceros

`ExchangeRateApiAdapter` (en `ventas/infra/externos/tasa_cambio.py`) recibe el formato propio
del proveedor (`{"result": "success", "rates": {"USD": ...}}`) y lo convierte
en el `TasaCambioDTO` del dominio. Nada fuera del adaptador conoce al proveedor.
`TasaCambioConRespaldo` agrega *fallback*: si el proveedor no responde se usa
una tasa configurable y la página sigue funcionando.

## 5. Comunicación asíncrona (Redis + Celery)

```mermaid
flowchart LR
    web[Django] -- ".delay()" --> broker[(Redis :6379/0)]
    beat[Celery Beat] -- "cada hora" --> broker
    broker --> worker[Worker Celery]
    worker -->|"notificar_cotizacion_aprobada<br/>notificar_cambio_etapa"| mail[Correo + tabla Notificacion]
    worker -->|generar_reporte_ventas| csv[(CSV en volumen media)]
    worker -->|crear_orden_pendiente<br/>reintento con backoff| fab[ms-fabricacion]
    worker -->|vencer_cotizaciones| pg[(PostgreSQL)]
```

| Tarea | Disparador | Resiliencia |
|---|---|---|
| `notificar_cotizacion_aprobada` | Cotización aprobada | Si el broker cae, la venta no falla (se registra el error) |
| `notificar_cambio_etapa` | Orden avanza de etapa | Idem |
| `generar_reporte_ventas` | Botón en `/procesos/` | El reporte queda en `ERROR` con el detalle; si ms-pagos cae se genera igual |
| `crear_orden_pendiente` | ms-fabricacion caído al aprobar | `autoretry` con backoff exponencial (hasta 8 intentos) |
| `vencer_cotizaciones` | Celery Beat, cada hora | Idempotente |

## 6. Resiliencia, en resumen

| Mecanismo | Dónde |
|---|---|
| Timeout en toda llamada HTTP | `ventas/infra/http/cliente.py` (`HTTP_TIMEOUT_SEGUNDOS`) |
| Reintentos con backoff (502/503/504 y errores de red) | `ventas/infra/http/cliente.py` (urllib3 `Retry`) |
| Circuit Breaker por servicio | `ventas/infra/http/circuit_breaker.py` (`CircuitBreaker`) |
| Idempotencia en escrituras | ms-catalogo `/reservas`, ms-pagos `/anticipos` `/saldos`, ms-fabricacion `/ordenes` |
| Saga con compensación | `ventas/services/cotizacion.py` (`_compensar`) → `/reservas/<ref>/liberar` |
| Degradación controlada en la UI | `ventas/views/` (avisos cuando un servicio no responde) |
| Fallback de la API de terceros | `TasaCambioConRespaldo` |
| Healthchecks y reinicio automático | `docker-compose.yml` (`healthcheck`, `restart: unless-stopped`) |
| Gateway: rate limit, reintento upstream y 503 JSON | `gateway/nginx.conf` |

## 7. Contratos de los microservicios

### ms-catalogo (`/api/catalogo`)
| Método | Ruta | Uso |
|---|---|---|
| GET | `/health` | Healthcheck |
| GET | `/productos`, `/productos/<id>` | Catálogo con `tipo_display` traducido |
| POST | `/productos` | Alta de producto (interno) |
| POST | `/cotizaciones/simular` | Precio sin apartar stock |
| POST | `/reservas` | Valida reglas, calcula precio y aparta stock (idempotente) |
| POST | `/reservas/<ref>/liberar` | Compensación |
| GET | `/publico/v1/productos` | **Servicio público para el equipo aliado** |

### ms-pagos (`/api/pagos`)
| Método | Ruta | Uso |
|---|---|---|
| GET | `/health` | Healthcheck (incluye la pasarela activa) |
| POST | `/anticipos` | Cobra el 50 %: 201 aprobado / 402 rechazado (idempotente) |
| POST | `/saldos` | Cobra el saldo; exige anticipo (409 si no hay) |
| GET | `/cobros?concepto_ref=` | Historial |
| GET | `/estado?refs=COT-1,COT-2` | Estado de pago en lote |

### ms-fabricacion (`/api/fabricacion`)
| Método | Ruta | Uso |
|---|---|---|
| GET | `/health`, `/etapas` | Healthcheck / secuencia traducida |
| POST | `/ordenes` | Abre orden (idempotente por `cotizacion_ref`) |
| GET | `/ordenes`, `/ordenes/<id>` | Listado / detalle con historial |
| POST | `/ordenes/<id>/avanzar` | Siguiente etapa (409 si ya fue entregada) |

Todas las respuestas de error tienen la forma `{"error": "<mensaje traducido>", "codigo": "<CODIGO>"}`
y respetan el encabezado `Accept-Language` (es/en).
