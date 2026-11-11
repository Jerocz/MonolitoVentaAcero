"""Pruebas del microservicio de fabricacion: creacion idempotente, etapas e i18n."""
import pytest

from app import create_app
from app.dominio.etapas import SECUENCIA_ETAPAS


@pytest.fixture
def cliente():
    return create_app("sqlite://").test_client()


ORDEN = {"cotizacion_ref": "COT-1", "cliente": "Hotel Poblado", "total": "240000"}


def test_health(cliente):
    assert cliente.get("/api/fabricacion/health").get_json()["estado"] == "ok"


def test_crear_orden_es_idempotente(cliente):
    r1 = cliente.post("/api/fabricacion/ordenes", json=ORDEN)
    assert r1.status_code == 201
    assert r1.get_json()["estado"] == "EN_COLA"
    r2 = cliente.post("/api/fabricacion/ordenes", json=ORDEN)
    assert r2.status_code == 200 and r2.get_json()["id"] == r1.get_json()["id"]


def test_avanza_todas_las_etapas_y_luego_409(cliente):
    orden_id = cliente.post("/api/fabricacion/ordenes", json=ORDEN).get_json()["id"]
    for esperado in SECUENCIA_ETAPAS[1:]:
        r = cliente.post(f"/api/fabricacion/ordenes/{orden_id}/avanzar")
        assert r.status_code == 200 and r.get_json()["estado"] == esperado
    assert r.get_json()["progreso"] == 100
    assert len(r.get_json()["eventos"]) == len(SECUENCIA_ETAPAS)
    assert cliente.post(f"/api/fabricacion/ordenes/{orden_id}/avanzar").status_code == 409


def test_orden_inexistente_404(cliente):
    assert cliente.post("/api/fabricacion/ordenes/99/avanzar").status_code == 404


def test_etapas_traducidas(cliente):
    en = cliente.get("/api/fabricacion/etapas", headers={"Accept-Language": "en"}).get_json()
    assert en[1]["estado_display"] == "Cutting"


def test_orden_invalida_400(cliente):
    assert cliente.post("/api/fabricacion/ordenes", json={"cliente": "x"}).status_code == 400
