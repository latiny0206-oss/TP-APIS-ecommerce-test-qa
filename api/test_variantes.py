"""
Tests de API para el endpoint /variantes.
Verifica estructura, detalle, stock y asociación con productos.
"""
from __future__ import annotations

import pytest


@pytest.mark.api
class TestListaVariantes:
    def test_get_variantes_devuelve_lista_no_vacia(self, client):
        resp = client.get("/variantes")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_cada_variante_tiene_campos_requeridos(self, client):
        resp = client.get("/variantes")
        assert resp.status_code == 200
        for v in resp.json():
            for campo in ("id", "talla", "color", "stock", "precio"):
                assert campo in v, f"Falta '{campo}' en variante id={v.get('id')}"

    def test_todas_las_variantes_tienen_producto_asociado(self, client):
        resp = client.get("/variantes")
        assert resp.status_code == 200
        for v in resp.json():
            assert v.get("productoId") is not None, (
                f"Variante {v['id']} no tiene productoId asociado"
            )


@pytest.mark.api
class TestDetalleVariante:
    def test_get_variante_por_id_valido(self, client):
        variantes = client.get("/variantes").json()
        assert variantes, "No hay variantes en el seed"
        vid = variantes[0]["id"]
        resp = client.get(f"/variantes/{vid}")
        assert resp.status_code == 200
        assert resp.json()["id"] == vid

    def test_get_variante_id_inexistente_devuelve_404(self, client):
        resp = client.get("/variantes/999999")
        assert resp.status_code == 404


@pytest.mark.api
class TestVarianteStock:
    def test_variante_con_stock_cero_es_valida(self, client):
        """La variante 11 (Linterna, producto PAUSADO) tiene stock=0 en el seed."""
        variantes = client.get("/variantes").json()
        sin_stock = [v for v in variantes if v["stock"] == 0]
        if not sin_stock:
            pytest.skip("No hay variantes con stock=0 en el seed")
        v = sin_stock[0]
        assert v["stock"] == 0
        # Debe seguir teniendo datos válidos
        assert v["precio"] > 0

    def test_variantes_stock_no_negativo(self, client):
        variantes = client.get("/variantes").json()
        for v in variantes:
            assert v["stock"] >= 0, f"Variante {v['id']} tiene stock negativo: {v['stock']}"
