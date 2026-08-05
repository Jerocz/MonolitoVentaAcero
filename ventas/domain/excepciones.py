class PedidoInvalidoError(Exception):
    """La cotizacion no cumple las reglas de negocio."""


class PagoRechazadoError(Exception):
    """La pasarela de pago rechazo el cobro."""
