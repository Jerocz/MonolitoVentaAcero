class PedidoInvalidoError(Exception):
    """La cotizacion no cumple las reglas de negocio."""


class PagoRechazadoError(Exception):
    """La pasarela de pago rechazo el cobro."""


def mensaje_de(error_validacion) -> str:
    """Aplana un ValidationError de Django (de un full_clean() de modelo)
    a un solo string, para que el dominio lo reporte como PedidoInvalidoError
    sin filtrar el tipo de excepcion de Django hacia la capa de presentacion."""
    if hasattr(error_validacion, "message_dict"):
        partes = [f"{campo}: {', '.join(msgs)}" for campo, msgs in error_validacion.message_dict.items()]
        return "; ".join(partes)
    return "; ".join(error_validacion.messages)
