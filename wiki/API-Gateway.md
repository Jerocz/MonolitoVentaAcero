# Visión de Escalabilidad: preparación para un API Gateway

Hoy el sistema es un monolito (Django sirviendo HTML y REST desde el
mismo proceso). Esta sección explica **qué decisiones de arquitectura ya
tomadas** hacen que ponerlo detrás de un API Gateway — o partirlo en
servicios más pequeños — sea un cambio de infraestructura, no una
reescritura del núcleo de negocio.

## 1. La API ya es la interfaz "de contrato", no un accesorio

`ventas/api.py` no es una capa delgada que reexporte `views.py`: es una
implementación independiente sobre `APIView`, con sus propios
serializers de entrada/salida (`serializers.py`) y sus propios códigos de
estado (201/400/404/409). Un Gateway (Kong, AWS API Gateway, NGINX+,
Apigee) necesita exactamente esto para poder:

- Enrutar por *path* (`/api/...`) sin tener que entender HTML.
- Validar/transformar el contrato JSON sin conocer la lógica de negocio.
- Cachear respuestas idempotentes (`GET /api/productos/`) sin arriesgar
  efectos secundarios.

Como las vistas HTML (`views.py`) y la API (`api.py`) llaman a los
**mismos servicios** (`CotizacionService`, `OrdenService`), el día que el
Gateway se ponga delante solo de `/api/`, la web de sustentación puede
seguir funcionando sin cambios, o retirarse sin afectar la API.

## 2. Todo lo que un Gateway maneja "por fuera" hoy no está duplicado adentro

Un Gateway típicamente centraliza: autenticación/JWT, rate limiting, TLS,
logging de acceso, y a veces transformación de payloads. Ninguna de esas
responsabilidades está mezclada en `services.py` ni en `domain/` — las
vistas (`api.py`) son delgadas a propósito (parsear request → llamar
servicio → mapear excepción a status code). Eso significa que agregar
autenticación (por ejemplo, `TokenAuthentication`/JWT de DRF, o
simplemente confiar en que el Gateway ya validó el token y lo reenvía en
un header) es un cambio **aditivo** en `api.py`/`settings.py`, no una
reestructuración del dominio.

## 3. El Service Layer ya es la costura para partir en microservicios

Si más adelante el negocio crece y "Fabricación" o "Pagos" necesitan
escalar o desplegarse por separado, el corte natural ya existe:

| Servicio futuro | Hoy vive en | Se convertiría en |
|---|---|---|
| `ventas-service` | `CotizacionService`, `CotizacionBuilder`, `domain/precios.py` | Servicio que expone `POST /cotizaciones` |
| `pagos-service` | `infra/pasarelas.py`, `infra/factories.py`, la parte de `OrdenService.pagar_saldo` | Servicio que expone `POST /pagos` (el Factory ya demuestra que la pasarela es un **adaptador reemplazable**: mañana ese adaptador podría ser un cliente HTTP a `pagos-service` en vez de una llamada a una pasarela externa directamente) |
| `fabricacion-service` | `OrdenFabricacion`, `OrdenService.avanzar_etapa` | Servicio que expone `POST /ordenes/{id}/avanzar` |

El Gateway sería quien enruta `/api/cotizaciones/*` → `ventas-service`,
`/api/ordenes/*/saldo` → `pagos-service`, etc., y quien agrega
autenticación y rate limiting **una sola vez**, en el borde, en lugar de
en cada servicio.

## 4. Lo que falta hoy (y hay que decirlo con honestidad en la sustentación)

Esta entrega es del núcleo de negocio, no de la infraestructura de
despliegue, así que **deliberadamente no** se implementó:

- **Versionado explícito de la API** (`/api/v1/...`). Es un cambio de
  una línea en `urls.py` cuando se necesite, pero hoy no existe.
- **Autenticación/autorización.** Las `APIView` no exigen token todavía.
  Un Gateway en producción normalmente terminaría el JWT y reenviaría un
  header (`X-User-Id`, `Authorization`) que las vistas usarían — pero eso
  requiere primero decidir el esquema de auth del curso.
- **Idempotencia declarada** (`Idempotency-Key`) en `POST /api/cotizaciones/`,
  que es lo que un Gateway o un cliente reintentando una petición fallida
  necesitaría para no crear dos cotizaciones iguales.
- **Health check** (`/health/`) para que el Gateway/balanceador sepa si
  la instancia está viva.

Ninguno de estos puntos exige tocar `domain/` o `services.py`: todos son
aditivos en `api.py`/`urls.py`/`settings.py`, que es justamente la prueba
de que la arquitectura actual ya separa "reglas de negocio" de
"preocupaciones de infraestructura de red".
