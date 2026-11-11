"""Excepciones de dominio. La capa de presentacion solo conoce estas, nunca
las de Django, `requests` o de un microservicio concreto."""


class PedidoInvalidoError(Exception):
    """La cotizacion no cumple las reglas de negocio."""


class PagoRechazadoError(Exception):
    """La pasarela de pago rechazo el cobro."""


class RecursoNoEncontradoError(Exception):
    """El recurso pedido (producto, orden...) no existe en el servicio duenio."""


class OperacionNoPermitidaError(Exception):
    """La operacion no aplica al estado actual (p. ej. avanzar una orden entregada)."""


class ServicioNoDisponibleError(Exception):
    """Un microservicio o API externa no respondio (caido, lento o circuito abierto)."""

    def __init__(self, servicio: str, detalle: str = ""):
        super().__init__(f"{servicio}: {detalle}" if detalle else servicio)
        self.servicio = servicio
        self.detalle = detalle


def mensaje_de(error_validacion) -> str:
    """Aplana un ValidationError de Django (de un full_clean() de modelo)
    a un solo string, para que el dominio lo reporte como PedidoInvalidoError
    sin filtrar el tipo de excepcion de Django hacia la capa de presentacion."""
    if hasattr(error_validacion, "message_dict"):
        partes = [f"{campo}: {', '.join(msgs)}" for campo, msgs in error_validacion.message_dict.items()]
        return "; ".join(partes)
    return "; ".join(error_validacion.messages)
