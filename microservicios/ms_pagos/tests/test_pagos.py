"""Pruebas del microservicio de pagos: anticipo, saldo, idempotencia, rechazo e i18n."""
import pytest

from app import create_app
from app.infra.pasarelas import PasarelaMock, PasarelaPago, ResultadoPago


class PasarelaRechaza(PasarelaPago):
    nombre = "PasarelaRechaza"

    def cobrar(self, monto, email_cliente):
        return ResultadoPago(False, "TEST-FAIL")


@pytest.fixture
def cliente():
    return create_app("sqlite://", pasarela=PasarelaMock()).test_client()


COBRO = {"concepto_ref": "COT-1", "total": "200000", "email": "cliente@test.co"}


def test_health(cliente):
    assert cliente.get("/api/pagos/health").get_json()["estado"] == "ok"


def test_anticipo_es_el_50_por_ciento_e_idempotente(cliente):
    r1 = cliente.post("/api/pagos/anticipos", json=COBRO)
    assert r1.status_code == 201
    assert r1.get_json()["monto"] == "100000.00"
    r2 = cliente.post("/api/pagos/anticipos", json=COBRO)
    assert r2.status_code == 200
    assert r2.get_json()["id"] == r1.get_json()["id"]


def test_saldo_requiere_anticipo(cliente):
    r = cliente.post("/api/pagos/saldos", json=COBRO, headers={"Accept-Language": "en"})
    assert r.status_code == 409
    assert "down payment" in r.get_json()["error"]


def test_saldo_y_estado(cliente):
    cliente.post("/api/pagos/anticipos", json=COBRO)
    r = cliente.post("/api/pagos/saldos", json=COBRO)
    assert r.status_code == 201 and r.get_json()["monto"] == "100000.00"
    estado = cliente.get("/api/pagos/estado?refs=COT-1,COT-9").get_json()
    assert estado["COT-1"] == {"anticipo_pagado": True, "saldo_pagado": True, "total_pagado": "200000.00"}
    assert estado["COT-9"]["anticipo_pagado"] is False


def test_pasarela_rechaza_devuelve_402():
    cliente = create_app("sqlite://", pasarela=PasarelaRechaza()).test_client()
    r = cliente.post("/api/pagos/anticipos", json=COBRO)
    assert r.status_code == 402
    assert r.get_json()["aprobado"] is False


def test_mock_rechaza_dominio_de_prueba(cliente):
    r = cliente.post("/api/pagos/anticipos", json=COBRO | {"email": "x@rechazo.test"})
    assert r.status_code == 402


def test_cuerpo_invalido_devuelve_400(cliente):
    assert cliente.post("/api/pagos/anticipos", json={"total": "-1"}).status_code == 400
