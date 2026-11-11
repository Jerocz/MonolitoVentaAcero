"""Adaptador HTTP de ms-pagos (implementa PagosPort)."""
from decimal import Decimal

from ventas.domain.dtos import CobroDTO, EstadoPagoDTO
from ventas.domain.excepciones import OperacionNoPermitidaError
from ventas.domain.puertos import PagosPort
from ventas.infra.http import ClienteHttp
from ventas.infra.microservicios.base import respuesta_inesperada as _respuesta_inesperada


class PagosHttpAdapter(PagosPort):
    NOMBRE = "ms-pagos"

    def __init__(self, url_base: str):
        self.http = ClienteHttp(self.NOMBRE, url_base)

    def _cobrar(self, ruta, referencia, total, email) -> CobroDTO:
        r = self.http.post(ruta, json={"concepto_ref": referencia, "total": str(total), "email": email})
        if r.status in (200, 201, 402):  # 402 = rechazado por la pasarela (respuesta valida)
            return CobroDTO(aprobado=bool(r.datos["aprobado"]), monto=Decimal(r.datos["monto"]),
                            referencia=r.datos["referencia"])
        if r.status in (400, 409):
            raise OperacionNoPermitidaError(r.mensaje_error)
        raise _respuesta_inesperada(self.NOMBRE, r)

    def cobrar_anticipo(self, referencia, total, email):
        return self._cobrar("/api/pagos/anticipos", referencia, total, email)

    def cobrar_saldo(self, referencia, total, email):
        return self._cobrar("/api/pagos/saldos", referencia, total, email)

    def estado(self, referencias):
        if not referencias:
            return {}
        r = self.http.get("/api/pagos/estado", refs=",".join(referencias))
        if r.status != 200:
            raise _respuesta_inesperada(self.NOMBRE, r)
        return {ref: EstadoPagoDTO(anticipo_pagado=v["anticipo_pagado"], saldo_pagado=v["saldo_pagado"])
                for ref, v in r.datos.items()}
