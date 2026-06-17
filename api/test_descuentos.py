import uuid
from datetime import date, timedelta

import pytest


def _payload_descuento(suffix: str | None = None) -> dict:
    s = suffix or uuid.uuid4().hex[:6]
    hoy = date.today()
    return {
        "nombre": f"Descuento Test {s}",
        "codigo": f"TEST{s.upper()}",
        "tipo": "PORCENTAJE",
        "valor": 10.0,
        "fechaInicio": hoy.isoformat(),
        "fechaFin": (hoy + timedelta(days=30)).isoformat(),
        "estado": "ACTIVO",
    }


@pytest.mark.api
class TestDescuentosActivos:
    def test_get_activos_sin_auth_devuelve_401(self, client):
        resp = client.get("/descuentos/activos")
        assert resp.status_code in (401, 403)

    def test_get_activos_autenticado_devuelve_lista(self, user_client):
        resp = user_client.get("/descuentos/activos")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_activos_solo_contienen_estado_activo(self, user_client):
        resp = user_client.get("/descuentos/activos")
        assert resp.status_code == 200
        for d in resp.json():
            assert d["estado"] == "ACTIVO", f"Descuento {d['codigo']} no es ACTIVO"

    def test_seed_otono2026_aparece_en_activos(self, user_client):
        resp = user_client.get("/descuentos/activos")
        assert resp.status_code == 200
        codigos = [d["codigo"] for d in resp.json()]
        assert "OTONO2026" in codigos

    def test_seed_fijo5000_aparece_en_activos(self, user_client):
        resp = user_client.get("/descuentos/activos")
        assert resp.status_code == 200
        codigos = [d["codigo"] for d in resp.json()]
        assert "FIJO5000" in codigos


@pytest.mark.api
class TestBuscarDescuento:
    def test_buscar_sin_auth_devuelve_401(self, client):
        resp = client.get("/descuentos/buscar", params={"codigo": "OTONO2026"})
        assert resp.status_code in (401, 403)

    def test_buscar_codigo_existente_devuelve_descuento(self, user_client):
        resp = user_client.get("/descuentos/buscar", params={"codigo": "OTONO2026"})
        assert resp.status_code == 200
        data = resp.json()
        # Puede devolver un objeto o una lista con un elemento
        if isinstance(data, list):
            assert len(data) > 0
            descuento = data[0]
        else:
            descuento = data
        assert descuento["codigo"] == "OTONO2026"
        assert descuento["tipo"] == "PORCENTAJE"
        assert descuento["valor"] == pytest.approx(15.0)

    def test_buscar_codigo_inexistente_devuelve_404_o_vacio(self, user_client):
        resp = user_client.get("/descuentos/buscar", params={"codigo": "CUPONINEXISTENTE999"})
        if resp.status_code == 200:
            data = resp.json()
            assert data == [] or data is None
        else:
            assert resp.status_code == 404

    def test_estructura_descuento_response(self, user_client):
        resp = user_client.get("/descuentos/buscar", params={"codigo": "FIJO5000"})
        assert resp.status_code == 200
        data = resp.json()
        descuento = data[0] if isinstance(data, list) else data
        for campo in ("id", "nombre", "codigo", "tipo", "valor", "fechaInicio", "fechaFin", "estado"):
            assert campo in descuento, f"Falta campo '{campo}' en DescuentoResponse"


@pytest.mark.api
class TestAdminDescuentos:
    def test_admin_puede_listar_todos_descuentos(self, admin_client):
        resp = admin_client.get("/descuentos")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_cliente_no_puede_listar_todos_descuentos(self, user_client):
        resp = user_client.get("/descuentos")
        assert resp.status_code in (401, 403)

    def test_admin_puede_crear_descuento(self, admin_client):
        payload = _payload_descuento()
        resp = admin_client.post("/descuentos", json=payload)
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert data["codigo"] == payload["codigo"]
        assert "id" in data

    def test_admin_puede_editar_descuento(self, admin_client):
        payload = _payload_descuento()
        create_resp = admin_client.post("/descuentos", json=payload)
        assert create_resp.status_code in (200, 201)
        descuento_id = create_resp.json()["id"]

        update = {**payload, "valor": 20.0}
        upd_resp = admin_client.put(f"/descuentos/{descuento_id}", json=update)
        assert upd_resp.status_code == 200
        assert upd_resp.json()["valor"] == pytest.approx(20.0)

    def test_admin_puede_eliminar_descuento(self, admin_client):
        payload = _payload_descuento()
        create_resp = admin_client.post("/descuentos", json=payload)
        assert create_resp.status_code in (200, 201)
        descuento_id = create_resp.json()["id"]

        del_resp = admin_client.delete(f"/descuentos/{descuento_id}")
        assert del_resp.status_code in (200, 204)
