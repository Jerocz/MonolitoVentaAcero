"""Errores del dominio del catalogo. Cada uno sabe con que codigo HTTP responder."""


class ErrorCatalogo(Exception):
    status = 400
    codigo = "SOLICITUD_INVALIDA"

    def __init__(self, mensaje, codigo=None):
        super().__init__(mensaje)
        self.mensaje = mensaje
        if codigo:
            self.codigo = codigo


class SolicitudInvalidaError(ErrorCatalogo):
    status = 400


class ProductoNoEncontradoError(ErrorCatalogo):
    status = 404
    codigo = "PRODUCTO_NO_EXISTE"


class ReservaNoEncontradaError(ErrorCatalogo):
    status = 404
    codigo = "RESERVA_NO_EXISTE"


class ReglaNegocioError(ErrorCatalogo):
    status = 409
    codigo = "REGLA_NEGOCIO"
