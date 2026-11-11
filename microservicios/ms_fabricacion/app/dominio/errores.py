"""Errores del dominio de fabricacion. Cada uno sabe con que codigo HTTP responder."""


class ErrorFabricacion(Exception):
    def __init__(self, status: int, codigo: str, mensaje: str):
        super().__init__(mensaje)
        self.status, self.codigo, self.mensaje = status, codigo, mensaje
