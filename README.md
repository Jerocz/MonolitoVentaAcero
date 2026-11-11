# Integrales Torres B. — Venta de acero inoxidable a la medida

**Entrega 2 — Migración a microservicios, integración y resiliencia.**

El monolito Django de la Entrega 1 evolucionó, con el **Strangler Pattern**, a un
ecosistema híbrido orquestado con Docker Compose y desplegado en AWS Academy (EC2):

| Contenedor | Tecnología | Responsabilidad |
|---|---|---|
| `gateway` | Nginx 1.27 | API Gateway: único punto de entrada (puerto 80), ruteo, rate limit, estáticos |
| `web` | Django 6 + DRF | Interfaz web, clientes y orquestación de la cotización (saga) |
| `ms_catalogo` | Flask | Catálogo, stock, Strategy de precios, reglas de la cotización, **servicio público** |
| `ms_pagos` | Flask | Pasarelas real/mock (Factory), anticipo 50 % y saldo |
| `ms_fabricacion` | Flask | Órdenes de fabricación y sus etapas |
| `worker` / `beat` | Celery | Notificaciones, reporte CSV, reintentos y vencimiento de cotizaciones |
| `redis` | Redis 7 | Message Broker + caché |
| `db` | PostgreSQL 16 | Una base de datos y un usuario **por servicio** |

Documentación:

- Diagramas (AWS, Nginx, Flask, Broker, saga, puertos y adaptadores): [`docs/arquitectura.md`](docs/arquitectura.md)
- Despliegue en AWS: [`docs/despliegue-aws.md`](docs/despliegue-aws.md)
- Auditoría UI/UX e i18n: [`docs/usabilidad-i18n.md`](docs/usabilidad-i18n.md)

## Correr con Docker (igual que en AWS)

```bash
cp .env.example .env          # cambia las claves
docker compose up -d --build
```

* Aplicación: http://localhost/
* Estado del ecosistema: http://localhost/salud/
* Servicio público para el equipo aliado: http://localhost/api/catalogo/publico/v1/productos

## Requisitos de la entrega y dónde están

| Requisito | Implementación |
|---|---|
| Docker Compose con Django, Flask, Nginx, BD y Broker | [`docker-compose.yml`](docker-compose.yml), [`Dockerfile`](Dockerfile), `microservicios/*/Dockerfile` |
| Despliegue en EC2 | [`deploy/aws/instalar_ec2.sh`](deploy/aws/instalar_ec2.sh), [`docs/despliegue-aws.md`](docs/despliegue-aws.md) |
| Strangler Pattern → Flask | [`microservicios/`](microservicios) + migración [`0003_strangler_...`](ventas/migrations/0003_strangler_extrae_catalogo_pagos_fabricacion.py) |
| Nginx como API Gateway | [`gateway/nginx.conf`](gateway/nginx.conf) |
| Servicio a proveer (JSON) | `GET /api/catalogo/publico/v1/productos` (ms-catalogo) |
| Servicio a consumir (aliado) | [`ventas/infra/aliado.py`](ventas/infra/aliado.py), página `/integraciones/` — se configura con `ALIADO_API_URL` |
| API de terceros vía Adapter (DIP) | [`ventas/domain/puertos.py`](ventas/domain/puertos.py) → [`ventas/infra/terceros.py`](ventas/infra/terceros.py) (tasa de cambio COP→USD) |
| Eventos con Redis/Celery | [`ventas/tasks.py`](ventas/tasks.py), [`monolito_venta_acero/celery.py`](monolito_venta_acero/celery.py), página `/procesos/` |
| Usabilidad / formularios robustos | [`ventas/forms.py`](ventas/forms.py), [`docs/usabilidad-i18n.md`](docs/usabilidad-i18n.md) |
| i18n con gettext, sin textos quemados | [`locale/`](locale), `microservicios/*/app/locales/`, prueba [`test_i18n.py`](ventas/tests/test_i18n.py) |
| Resiliencia | timeout + retry + circuit breaker ([`ventas/infra/http.py`](ventas/infra/http.py)), saga con compensación ([`ventas/services.py`](ventas/services.py)), healthchecks |

## Correr sin Docker (desarrollo)

```bash
pip install -r requirements.txt
python manage.py migrate && python seed.py
# En otras 3 terminales, cada microservicio (usa SQLite local):
cd microservicios/ms_catalogo    && pip install -r requirements.txt && python -m app.init_db && flask --app wsgi run -p 5001
cd microservicios/ms_pagos       && python -m app.init_db && flask --app wsgi run -p 5002
cd microservicios/ms_fabricacion && python -m app.init_db && flask --app wsgi run -p 5003
python manage.py runserver
# Opcional (tareas en segundo plano): redis-server y  celery -A monolito_venta_acero worker -l info
```

Si un microservicio o Redis no está corriendo, la página no se cae: muestra un
aviso y sigue funcionando con lo que sí está disponible.

## Pruebas

```bash
python manage.py test ventas                                   # monolito (53 pruebas)
cd microservicios/ms_catalogo    && python -m pytest           # 11 pruebas
cd microservicios/ms_pagos       && python -m pytest           # 7 pruebas
cd microservicios/ms_fabricacion && python -m pytest           # 6 pruebas
```

## Estructura

```
gateway/nginx.conf              API Gateway
docker-compose.yml, Dockerfile  orquestación
docker/postgres/                una BD + usuario por servicio
deploy/aws/                     script de instalación en EC2
docs/                           arquitectura, despliegue, usabilidad e i18n
monolito_venta_acero/           settings (12-factor), urls, celery
ventas/
  models.py                     Cliente, Cotizacion, ItemCotizacion, Notificacion, ReporteVentas
  services.py                   saga de cotización + OrdenService
  domain/puertos.py             interfaces (DIP) y DTOs
  infra/                        adaptadores HTTP, Adapter de terceros, aliado, Celery, contenedor
  tasks.py                      tareas Celery
  forms.py, views.py, api.py    presentación (HTML y DRF)
  templates/, static/           UI bilingüe
locale/en/                      traducciones del monolito
microservicios/
  ms_catalogo/  ms_pagos/  ms_fabricacion/   (Flask + SQLAlchemy + pytest)
```

## Datos de demostración

* `seed.py` crea 5 clientes. **Cliente Prueba Rechazo** (`pagos@rechazo.test`) hace que la
  pasarela simulada rechace el pago: sirve para mostrar la compensación de la saga
  (el stock reservado se devuelve y la cotización queda *Rechazada*).
* ms-catalogo carga 4 productos al arrancar.
* Para la pasarela "real": `ENV_TYPE=REAL` en `.env`.
