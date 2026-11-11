"""Casos de uso de cobro: aplican las reglas del dominio, llaman a la pasarela
y registran cada intento. Las rutas solo traducen HTTP <-> estas funciones."""
from decimal import Decimal

from sqlalchemy import select

from app.dominio.errores import ErrorPagos
from app.dominio.reglas import calcular_anticipo, calcular_saldo
from app.i18n import _
from app.infra.pasarelas import PasarelaPago
from app.modelos import Cobro


class ServicioCobros:
    def __init__(self, sesion, pasarela: PasarelaPago):
        self.s = sesion
        self.pasarela = pasarela

    def _aprobado(self, concepto: str, tipo: str) -> Cobro | None:
        return self.s.scalar(select(Cobro).where(
            Cobro.concepto_ref == concepto, Cobro.tipo == tipo, Cobro.aprobado.is_(True)))

    def _cobrar(self, concepto: str, tipo: str, monto: Decimal, email: str) -> Cobro:
        resultado = self.pasarela.cobrar(monto, email)
        cobro = Cobro(concepto_ref=concepto, tipo=tipo, monto=monto, email=email,
                      aprobado=resultado.aprobado, referencia=resultado.referencia,
                      pasarela=self.pasarela.nombre)
        self.s.add(cobro)
        self.s.flush()
        return cobro

    def anticipo(self, concepto: str, total: Decimal, email: str) -> tuple[Cobro, bool]:
        """Cobra el 50% del total. Idempotente: devuelve (cobro, es_nuevo)."""
        previo = self._aprobado(concepto, Cobro.ANTICIPO)
        if previo:
            return previo, False
        return self._cobrar(concepto, Cobro.ANTICIPO, calcular_anticipo(total), email), True

    def saldo(self, concepto: str, total: Decimal, email: str) -> tuple[Cobro, bool]:
        """Cobra el saldo final. Requiere anticipo aprobado; idempotente."""
        if not self._aprobado(concepto, Cobro.ANTICIPO):
            raise ErrorPagos(409, "SIN_ANTICIPO",
                             _("No se puede cobrar el saldo de {ref}: no tiene anticipo aprobado.", ref=concepto))
        previo = self._aprobado(concepto, Cobro.SALDO)
        if previo:
            return previo, False
        return self._cobrar(concepto, Cobro.SALDO, calcular_saldo(total), email), True

    def historial(self, concepto: str | None = None) -> list[Cobro]:
        consulta = select(Cobro).order_by(Cobro.id.desc()).limit(100)
        if concepto:
            consulta = consulta.where(Cobro.concepto_ref == concepto)
        return list(self.s.scalars(consulta))

    def estado(self, refs: list[str]) -> dict:
        resultado = {r: {"anticipo_pagado": False, "saldo_pagado": False, "total_pagado": Decimal("0")}
                     for r in refs}
        if refs:
            for c in self.s.scalars(select(Cobro).where(Cobro.concepto_ref.in_(refs), Cobro.aprobado.is_(True))):
                fila = resultado[c.concepto_ref]
                fila["anticipo_pagado" if c.tipo == Cobro.ANTICIPO else "saldo_pagado"] = True
                fila["total_pagado"] += Decimal(c.monto)
        return resultado
