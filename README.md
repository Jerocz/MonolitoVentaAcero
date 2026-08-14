# Integrales Torres B. — Monolito de venta de acero inoxidable

Monolito Django con procesamiento de pagos para una empresa de acero inoxidable a la medida.

## Como correrlo

```bash
pip install -r requirements.txt
python manage.py migrate
python seed.py            # datos de ejemplo (clientes y productos)
python manage.py runserver
```

Abre http://127.0.0.1:8000/

Para usar la pasarela real en vez de la mock:

```bash
# Windows (PowerShell)
$env:ENV_TYPE="REAL"; python manage.py runserver
# Linux / macOS
ENV_TYPE=REAL python manage.py runserver
```

## Que cambio en esta version

- **Marca**: la pagina es ahora Integrales Torres B., con el logo y la paleta
  de la marca (negro carbon #0E0E0C, crema #F0E2C3).
- **Nuevo diseno** de `ventas/templates/ventas/venta_form.html`: portada,
  catalogo de productos, cotizador, tabla de ordenes con barra de progreso
  y tabla de cotizaciones. Todo en un solo archivo, sin dependencias nuevas
  de frontend.
- **Logos e imagenes** en `ventas/static/ventas/` (`logo-lockup.png`,
  `logo-mark.png`, `cocina.png`).
- `django.contrib.humanize` agregado a `INSTALLED_APPS` para formatear los
  precios con separador de miles.
- `seed.py` crea tambien dos clientes persona natural.

La logica de negocio no se toco: `services.py`, `domain/` (Strategy de precios,
Builder de cotizacion, reglas) e `infra/` (Factory de pasarelas) quedan igual.

## Estructura

```
monolito_venta_acero/   settings, urls, wsgi
ventas/
  models.py             modelos anemicos (Cliente, Producto, Cotizacion, Orden, Pago)
  services.py           Service Layer (CotizacionService, OrdenService)
  domain/               precios (Strategy), builders, reglas, excepciones
  infra/                pasarelas de pago + Factory
  api.py                API REST (DRF)
  views.py              vistas HTML
  templates/ventas/     venta_form.html  <- el diseno nuevo
  static/ventas/        logos e imagenes
```
