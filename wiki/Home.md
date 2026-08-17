# Wiki Técnica — Integrales Torres B. (Monolito Venta de Acero)

Documentación de arquitectura para la Entrega No. 1 (Núcleo de Negocio y
Exposición de API Profesional).

> **Cómo usar esta carpeta**: cada archivo corresponde a una página de la
> Wiki de GitHub. Si el profesor exige la Wiki nativa de GitHub (el repo
> `MonolitoVentaAcero.wiki.git`), copia el contenido de cada `.md` a una
> página nueva con el mismo nombre — ya están en formato de título de
> página de Wiki (`Palabras-Con-Guion.md`).

## Páginas

1. [Estructura de Carpetas](Estructura-de-Carpetas.md) — por qué el
   código está dividido en `domain/`, `infra/`, `services.py`, `api.py`.
2. [Diagrama de Secuencia — Crear Cotización](Diagrama-de-Secuencia-Cotizacion.md)
   — la funcionalidad más compleja del sistema, capa por capa.
3. [Visión de Escalabilidad — API Gateway](API-Gateway.md) — cómo esta
   API ya está lista para vivir detrás de un Gateway, y qué falta.

## Resumen del núcleo implementado

| Requisito | Dónde vive | Estado |
|---|---|---|
| Modelos de dominio (50-60%) | `ventas/models.py` | 10 entidades: `Cliente`, `Producto`, `Lamina`, `Meson`, `Campana`, `Freidora`, `Cotizacion`, `ItemCotizacion`, `OrdenFabricacion`, `Pago` |
| Validación a nivel de modelo | `ventas/models.py` (`save()` → `full_clean()`) | Cada entidad se autovalida antes de persistir (tipos, rangos, choices) |
| Service Layer (SRP) | `ventas/services.py` | `CotizacionService`, `OrdenService` — nada de lógica de negocio en `views.py`/`api.py`/`serializers.py` |
| DRF: `APIView` + códigos HTTP | `ventas/api.py` | 201 (creado), 400 (payload inválido), 404 (no existe), 409 (regla de negocio violada) |
| Builder (obligatorio) | `ventas/domain/builders.py` | `CotizacionBuilder` — construye y valida la entidad más compleja del sistema |
| Factory (obligatorio) | `ventas/infra/factories.py` | `PasarelaPagoFactory` — elige `PasarelaReal`/`PasarelaMock` según `ENV_TYPE` |
| Bonus: Strategy | `ventas/domain/precios.py` | `EstrategiaPrecio` por tipo de producto (no es un patrón pedido, pero refuerza OCP) |

11 pruebas automatizadas (`python manage.py test ventas`) cubren: inyección
de dependencias en los servicios, la estrategia de precio, la validación a
nivel de modelo y los cuatro códigos de estado HTTP de la rúbrica.
