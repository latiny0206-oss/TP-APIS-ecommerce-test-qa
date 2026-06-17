import pytest


DATOS_ENVIO = {
    "nombreDestinatario": "Test User",
    "direccion": "Calle Falsa 123",
    "ciudad": "Córdoba",
    "provincia": "Córdoba",
    "codigoPostal": "5000",
    "telefono": "3515559999",
    "metodoPago": "EFECTIVO",
}


def _primera_variante_con_stock(client) -> dict:
    variantes = client.get("/variantes").json()
    for v in variantes:
        if v.get("stock", 0) > 0:
            return v
    pytest.skip("No hay variantes con stock disponible")


def _crear_orden(client, usuario_id: int) -> dict:
    """Crea un carrito con un item y hace checkout. Devuelve la OrdenResponse."""
    carrito_resp = client.post("/carritos", json={"usuarioId": usuario_id})
    assert carrito_resp.status_code in (200, 201)
    carrito_id = carrito_resp.json()["id"]

    variante = _primera_variante_con_stock(client)
    client.post(
        f"/carritos/{carrito_id}/items",
        json={"idVariante": variante["id"], "cantidad": 1},
    )

    resp = client.post(f"/carritos/{carrito_id}/checkout", json=DATOS_ENVIO)
    assert resp.status_code in (200, 201), f"Checkout falló: {resp.text}"
    return resp.json()


@pytest.mark.api
class TestOrdenes:
    def test_usuario_puede_ver_sus_propias_ordenes(self, new_user_client):
        user_id = new_user_client._auth_data["id"]
        orden = _crear_orden(new_user_client, user_id)

        resp = new_user_client.get("/ordenes")
        assert resp.status_code == 200
        ids = [o["id"] for o in resp.json()]
        assert orden["id"] in ids

    def test_usuario_no_puede_ver_ordenes_de_otro_usuario(self, user_client, new_user_client):
        # new_user_client crea su orden
        new_id = new_user_client._auth_data["id"]
        orden_nueva = _crear_orden(new_user_client, new_id)

        # user_client (juanperez) no debe ver la orden del nuevo usuario
        resp = user_client.get("/ordenes")
        assert resp.status_code == 200
        ids = [o["id"] for o in resp.json()]
        assert orden_nueva["id"] not in ids

    def test_usuario_no_puede_acceder_a_orden_ajena(self, user_client, new_user_client):
        new_id = new_user_client._auth_data["id"]
        orden_nueva = _crear_orden(new_user_client, new_id)

        resp = user_client.get(f"/ordenes/{orden_nueva['id']}")
        assert resp.status_code in (403, 404)

    def test_admin_puede_ver_todas_las_ordenes(self, admin_client, new_user_client):
        new_id = new_user_client._auth_data["id"]
        orden = _crear_orden(new_user_client, new_id)

        resp = admin_client.get("/ordenes")
        assert resp.status_code == 200
        ids = [o["id"] for o in resp.json()]
        assert orden["id"] in ids

    def test_admin_puede_confirmar_orden_pendiente(self, admin_client, new_user_client):
        new_id = new_user_client._auth_data["id"]
        orden = _crear_orden(new_user_client, new_id)
        assert orden["estado"] == "PENDIENTE"

        resp = admin_client.post(f"/ordenes/{orden['id']}/confirmar")
        assert resp.status_code == 200
        assert resp.json()["estado"] == "CONFIRMADA"

    def test_admin_puede_cancelar_orden(self, admin_client, new_user_client):
        new_id = new_user_client._auth_data["id"]
        orden = _crear_orden(new_user_client, new_id)

        # Necesitamos stock de la variante antes de cancelar
        variante_id = orden["items"][0]["varianteId"]
        stock_antes = admin_client.get(f"/variantes/{variante_id}").json()["stock"]

        resp = admin_client.post(f"/ordenes/{orden['id']}/cancelar")
        assert resp.status_code == 200
        assert resp.json()["estado"] == "CANCELADA"

        # Stock debe restaurarse
        stock_despues = admin_client.get(f"/variantes/{variante_id}").json()["stock"]
        assert stock_despues == stock_antes + 1

    def test_usuario_puede_cancelar_su_propia_orden_pendiente(self, new_user_client):
        new_id = new_user_client._auth_data["id"]
        orden = _crear_orden(new_user_client, new_id)
        assert orden["estado"] == "PENDIENTE"

        resp = new_user_client.post(f"/ordenes/{orden['id']}/cancelar")
        assert resp.status_code == 200
        assert resp.json()["estado"] == "CANCELADA"

    def test_get_ordenes_sin_auth_devuelve_401(self, client):
        resp = client.get("/ordenes")
        assert resp.status_code == 401

    def test_estructura_orden_response(self, new_user_client):
        new_id = new_user_client._auth_data["id"]
        orden = _crear_orden(new_user_client, new_id)

        for campo in ("id", "usuarioId", "fechaCreacion", "montoFinal", "estado", "items"):
            assert campo in orden, f"Falta '{campo}' en OrdenResponse"

        assert isinstance(orden["items"], list)
        assert len(orden["items"]) > 0

        item = orden["items"][0]
        for campo_item in ("id", "varianteId", "cantidad", "precioAlMomento"):
            assert campo_item in item, f"Falta '{campo_item}' en ItemOrdenResponse"
