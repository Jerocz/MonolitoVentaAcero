"""Reglas de fabricacion (migradas desde ventas/domain/reglas.py y
OrdenService.avanzar_etapa del monolito)."""
from datetime import date, timedelta

SECUENCIA_ETAPAS = ["EN_COLA", "CORTE", "SOLDADURA", "PULIDO", "TERMINADA", "ENTREGADA"]
DIAS_FABRICACION = 20


class EtapaFinalError(Exception):
    """La orden ya esta en la ultima etapa."""


def etapa_inicial() -> str:
    return SECUENCIA_ETAPAS[0]


def siguiente_etapa(actual: str) -> str:
    i = SECUENCIA_ETAPAS.index(actual)
    if i >= len(SECUENCIA_ETAPAS) - 1:
        raise EtapaFinalError(actual)
    return SECUENCIA_ETAPAS[i + 1]


def fecha_estimada(desde: date | None = None) -> date:
    return (desde or date.today()) + timedelta(days=DIAS_FABRICACION)


def progreso(estado: str) -> int:
    """Porcentaje de avance (0-100) segun la etapa."""
    return round(SECUENCIA_ETAPAS.index(estado) * 100 / (len(SECUENCIA_ETAPAS) - 1))
