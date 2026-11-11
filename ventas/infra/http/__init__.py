"""Comunicacion HTTP resiliente (timeout, reintentos y circuit breaker)."""
from ventas.infra.http.circuit_breaker import CircuitBreaker, breaker_para, estado_circuitos
from ventas.infra.http.cliente import ClienteHttp, RespuestaHttp

__all__ = ["CircuitBreaker", "ClienteHttp", "RespuestaHttp", "breaker_para", "estado_circuitos"]
