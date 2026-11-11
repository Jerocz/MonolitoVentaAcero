"""Servicios externos al monolito: microservicios, API de terceros y equipo aliado."""
from monolito_venta_acero.settings.entorno import env_decimal, env_entero, env_texto

MICROSERVICIOS = {
    "CATALOGO": env_texto("MS_CATALOGO_URL", "http://localhost:5001"),
    "PAGOS": env_texto("MS_PAGOS_URL", "http://localhost:5002"),
    "FABRICACION": env_texto("MS_FABRICACION_URL", "http://localhost:5003"),
}

# Timeout, reintentos y circuit breaker de toda llamada HTTP (ventas/infra/http/).
RESILIENCIA = {
    "TIMEOUT_SEGUNDOS": env_decimal("HTTP_TIMEOUT_SEGUNDOS", 4),
    "REINTENTOS": env_entero("HTTP_REINTENTOS", 2),
    "UMBRAL_FALLOS": env_entero("CIRCUITO_UMBRAL_FALLOS", 3),
    "SEGUNDOS_CIRCUITO_ABIERTO": env_entero("CIRCUITO_SEGUNDOS_ABIERTO", 20),
}

# API de terceros (consumida con el patron Adapter).
TASA_CAMBIO_API_URL = env_texto("TASA_CAMBIO_API_URL", "https://open.er-api.com")
TASA_COP_USD_RESPALDO = env_texto("TASA_COP_USD_RESPALDO", "0.00025")

# Servicio que expone el equipo aliado.
ALIADO_NOMBRE = env_texto("ALIADO_NOMBRE", "Equipo aliado")
ALIADO_API_URL = env_texto("ALIADO_API_URL")
