"""Pruebas del microservicio de catalogo: estrategias, reglas, reservas e i18n."""
from decimal import Decimal

import pytest

from app import create_app
from app.dominio.precios import estrategia_para
from app.init_db import inicializar


@pytest.fixture
def cliente():
    app = create_app("sqlite://")
    inicializar(app.extensions["db"])
    return app.test_client()


def _ids(cliente):
    return {p["tipo"]: p["id"] for p in cliente.get("/api/catalogo/productos").get_json()}


def test_health(cliente):
    r = cliente.get("/api/catalogo/health")
    assert r.status_code == 200
    assert r.get_json()["estado"] == "ok"


def test_lista_productos_con_tipo_traducido(cliente):
    es = cliente.get("/api/catalogo/productos", headers={"Accept-Language": "es"}).get_json()
    en = cliente.get("/api/catalogo/productos", headers={"Accept-Language": "en"}).get_json()
    assert len(es) == 4
    assert es[0]["tipo_display"] == "Lámina a la medida"
    assert en[0]["tipo_display"] == "Custom-cut sheet"


def test_strategy_meson_cuesta_15_por_ciento_mas():
    lamina = estrategia_para("LAMINA").calcular(Decimal("100000"), 100, 100, 1)
    meson = estrategia_para("MESON").calcular(Decimal("100000"), 100, 100, 1)
    assert meson == (lamina * Decimal("1.15")).quantize(Decimal("0.01"))


def test_freidora_no_es_a_medida_y_consume_unidades():
    estrategia = estrategia_para("FREIDORA")
    assert estrategia.es_a_medida is False
    assert estrategia.consumo_stock(10, 10, 3) == 3


def test_reserva_descuenta_stock_y_es_idempotente(cliente):
    ids = _ids(cliente)
    cuerpo = {"referencia": "COT-1", "items": [
        {"producto_id": ids["LAMINA"], "ancho_cm": 100, "largo_cm": 100, "cantidad": 1}]}
    r1 = cliente.post("/api/catalogo/reservas", json=cuerpo)
    assert r1.status_code == 201
    assert r1.get_json()["total"] == "120000.00"
    r2 = cliente.post("/api/catalogo/reservas", json=cuerpo)
    assert r2.status_code == 200  # misma reserva, no descuenta dos veces
    stock = cliente.get(f"/api/catalogo/productos/{ids['LAMINA']}").get_json()["stock_m2"]
    assert stock == "59.00"


def test_liberar_reserva_devuelve_stock(cliente):
    ids = _ids(cliente)
    cliente.post("/api/catalogo/reservas", json={"referencia": "COT-2", "items": [
        {"producto_id": ids["MESON"], "ancho_cm": 200, "largo_cm": 100, "cantidad": 2}]})
    r = cliente.post("/api/catalogo/reservas/COT-2/liberar")
    assert r.status_code == 200 and r.get_json()["estado"] == "LIBERADA"
    stock = cliente.get(f"/api/catalogo/productos/{ids['MESON']}").get_json()["stock_m2"]
    assert stock == "60.00"


def test_ancho_minimo_devuelve_409_traducido(cliente):
    ids = _ids(cliente)
    cuerpo = {"referencia": "COT-3", "items": [
        {"producto_id": ids["LAMINA"], "ancho_cm": 30, "largo_cm": 100}]}
    r = cliente.post("/api/catalogo/reservas", json=cuerpo, headers={"Accept-Language": "en"})
    assert r.status_code == 409
    assert r.get_json()["codigo"] == "ANCHO_MINIMO"
    assert "minimum width" in r.get_json()["error"]


def test_stock_insuficiente_devuelve_409(cliente):
    ids = _ids(cliente)
    r = cliente.post("/api/catalogo/reservas", json={"referencia": "COT-4", "items": [
        {"producto_id": ids["LAMINA"], "ancho_cm": 1000, "largo_cm": 1000}]})
    assert r.status_code == 409
    assert r.get_json()["codigo"] == "STOCK_INSUFICIENTE"


def test_producto_inexistente_devuelve_404(cliente):
    r = cliente.post("/api/catalogo/reservas", json={"referencia": "COT-5", "items": [
        {"producto_id": 999, "ancho_cm": 100, "largo_cm": 100}]})
    assert r.status_code == 404


def test_cuerpo_invalido_devuelve_400(cliente):
    assert cliente.post("/api/catalogo/reservas", json={"referencia": "X", "items": []}).status_code == 400
    assert cliente.post("/api/catalogo/reservas", data="no-json").status_code == 400


def test_endpoint_publico_para_equipo_aliado(cliente):
    r = cliente.get("/api/catalogo/publico/v1/productos")
    datos = r.get_json()
    assert r.status_code == 200
    assert datos["moneda"] == "COP"
    assert datos["total_productos"] == 4
    assert {"id", "nombre", "precio_base_m2", "disponible"} <= set(datos["productos"][0])
