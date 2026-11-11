"""Reglas que se quedan en el monolito (las de precio, stock, pagos y
fabricacion se migraron a los microservicios)."""

DIAS_VIGENCIA_COTIZACION = 15


def referencia_cotizacion(cotizacion_id: int) -> str:
    """Identificador compartido entre servicios para una cotizacion."""
    return f"COT-{cotizacion_id}"


def id_desde_referencia(referencia: str) -> int | None:
    prefijo = "COT-"
    if referencia and referencia.startswith(prefijo) and referencia[len(prefijo):].isdigit():
        return int(referencia[len(prefijo):])
    return None
