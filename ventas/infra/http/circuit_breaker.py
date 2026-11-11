"""Circuit Breaker: tras N fallos seguidos deja de llamar al servicio durante un
tiempo y responde de inmediato con ServicioNoDisponibleError (fail fast).

    CERRADO --(N fallos)--> ABIERTO --(espera)--> SEMI_ABIERTO --(exito)--> CERRADO
"""
import logging
import threading
import time

from django.conf import settings

log = logging.getLogger(__name__)


class CircuitBreaker:
    CERRADO, ABIERTO, SEMI_ABIERTO = "CERRADO", "ABIERTO", "SEMI_ABIERTO"

    def __init__(self, nombre, umbral_fallos=3, segundos_abierto=20, reloj=time.monotonic):
        self.nombre = nombre
        self.umbral_fallos = umbral_fallos
        self.segundos_abierto = segundos_abierto
        self._reloj = reloj
        self._fallos = 0
        self._abierto_desde = None
        self._lock = threading.Lock()

    @property
    def estado(self):
        with self._lock:
            if self._abierto_desde is None:
                return self.CERRADO
            if self._reloj() - self._abierto_desde >= self.segundos_abierto:
                return self.SEMI_ABIERTO  # se deja pasar una llamada de prueba
            return self.ABIERTO

    def permite_llamada(self) -> bool:
        return self.estado != self.ABIERTO

    def registrar_exito(self):
        with self._lock:
            self._fallos = 0
            self._abierto_desde = None

    def registrar_fallo(self):
        with self._lock:
            self._fallos += 1
            if self._fallos >= self.umbral_fallos:
                if self._abierto_desde is None:
                    log.warning("Circuit breaker ABIERTO para %s", self.nombre)
                self._abierto_desde = self._reloj()


_breakers: dict[str, CircuitBreaker] = {}
_registro_lock = threading.Lock()


def breaker_para(nombre: str) -> CircuitBreaker:
    with _registro_lock:
        if nombre not in _breakers:
            _breakers[nombre] = CircuitBreaker(
                nombre,
                umbral_fallos=settings.RESILIENCIA["UMBRAL_FALLOS"],
                segundos_abierto=settings.RESILIENCIA["SEGUNDOS_CIRCUITO_ABIERTO"])
        return _breakers[nombre]


def estado_circuitos() -> dict[str, str]:
    return {nombre: b.estado for nombre, b in _breakers.items()}
