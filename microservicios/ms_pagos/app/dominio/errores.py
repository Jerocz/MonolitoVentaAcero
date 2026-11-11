"""Errores del dominio de pagos. Cada uno sabe con que codigo HTTP responder."""


class ErrorPagos(Exception):
    def __init__(self, status: int, codigo: str, mensaje: str):
        super().__init__(mensaje)
        self.status, self.codigo, self.mensaje = status, codigo, mensaje
