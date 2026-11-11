"""API HTTP del microservicio de pagos (JSON)."""
from decimal import Decimal, InvalidOperation

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import select

from app.dominio.reglas import calcular_anticipo, calcular_saldo
from app.i18n import _
from app.modelos import Cobro

bp = Blueprint("pagos", __name__, url_prefix="/api/pagos")


class ErrorPagos(Exception):
    def __init__(self, status, codigo, mensaje):
        super().__init__(mensaje)
        self.status, self.codigo, self.mensaje = status, codigo, mensaje


@bp.errorhandler(ErrorPagos)
def _manejar(error: ErrorPagos):
    return jsonify({"error": error.mensaje, "codigo": error.codigo}), error.status


def _db():
    return current_app.extensions["db"]


def _pasarela():
    return current_app.extensions["pasarela"]


def cobro_json(c: Cobro) -> dict:
    return {
        "id": c.id,
        "concepto_ref": c.concepto_ref,
        "tipo": c.tipo,
        "monto": str(Decimal(c.monto).quantize(Decimal("0.01"))),
        "aprobado": c.aprobado,
        "referencia": c.referencia,
        "pasarela": c.pasarela,
        "creado": c.creado.isoformat(timespec="seconds") if c.creado else None,
    }


def _entrada():
    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        raise ErrorPagos(400, "JSON_INVALIDO", _("El cuerpo debe ser un objeto JSON."))
    try:
        concepto = str(datos["concepto_ref"]).strip()
        total = Decimal(str(datos["total"]))
        email = str(datos["email"]).strip()
    except (KeyError, InvalidOperation, ValueError):
        raise ErrorPagos(400, "COBRO_INVALIDO", _("Se requieren concepto_ref, total y email."))
    if not concepto or total <= 0 or "@" not in email:
        raise ErrorPagos(400, "COBRO_INVALIDO", _("Se requieren concepto_ref, total y email."))
    return concepto, total, email


def _aprobado(s, concepto, tipo):
    return s.scalar(select(Cobro).where(
        Cobro.concepto_ref == concepto, Cobro.tipo == tipo, Cobro.aprobado.is_(True)))


def _cobrar(s, concepto, tipo, monto, email):
    resultado = _pasarela().cobrar(monto, email)
    cobro = Cobro(concepto_ref=concepto, tipo=tipo, monto=monto, email=email,
                  aprobado=resultado.aprobado, referencia=resultado.referencia,
                  pasarela=_pasarela().nombre)
    s.add(cobro)
    s.flush()
    # 201 = cobrado; 402 Payment Required = la pasarela lo rechazo (queda registrado).
    return jsonify(cobro_json(cobro)), (201 if cobro.aprobado else 402)


@bp.get("/health")
def salud():
    with _db().sesion() as s:
        s.execute(select(1))
    return jsonify({"servicio": "ms-pagos", "estado": "ok", "pasarela": _pasarela().nombre})


@bp.post("/anticipos")
def cobrar_anticipo():
    """Cobra el 50% del total. Idempotente: si ya hay anticipo aprobado, lo devuelve."""
    concepto, total, email = _entrada()
    with _db().sesion() as s:
        previo = _aprobado(s, concepto, Cobro.ANTICIPO)
        if previo:
            return jsonify(cobro_json(previo)), 200
        return _cobrar(s, concepto, Cobro.ANTICIPO, calcular_anticipo(total), email)


@bp.post("/saldos")
def cobrar_saldo():
    """Cobra el saldo final. Requiere anticipo aprobado; idempotente."""
    concepto, total, email = _entrada()
    with _db().sesion() as s:
        if not _aprobado(s, concepto, Cobro.ANTICIPO):
            raise ErrorPagos(409, "SIN_ANTICIPO",
                             _("No se puede cobrar el saldo de {ref}: no tiene anticipo aprobado.", ref=concepto))
        previo = _aprobado(s, concepto, Cobro.SALDO)
        if previo:
            return jsonify(cobro_json(previo)), 200
        return _cobrar(s, concepto, Cobro.SALDO, calcular_saldo(total), email)


@bp.get("/cobros")
def listar_cobros():
    concepto = request.args.get("concepto_ref")
    with _db().sesion() as s:
        consulta = select(Cobro).order_by(Cobro.id.desc()).limit(100)
        if concepto:
            consulta = consulta.where(Cobro.concepto_ref == concepto)
        return jsonify([cobro_json(c) for c in s.scalars(consulta)])


@bp.get("/estado")
def estado():
    """Estado de pago de varias cotizaciones a la vez: ?refs=COT-1,COT-2"""
    refs = [r.strip() for r in request.args.get("refs", "").split(",") if r.strip()][:100]
    resultado = {r: {"anticipo_pagado": False, "saldo_pagado": False, "total_pagado": "0.00"} for r in refs}
    if refs:
        with _db().sesion() as s:
            for c in s.scalars(select(Cobro).where(Cobro.concepto_ref.in_(refs), Cobro.aprobado.is_(True))):
                fila = resultado[c.concepto_ref]
                fila["anticipo_pagado" if c.tipo == Cobro.ANTICIPO else "saldo_pagado"] = True
                fila["total_pagado"] = str((Decimal(fila["total_pagado"]) + Decimal(c.monto)).quantize(Decimal("0.01")))
    return jsonify(resultado)
