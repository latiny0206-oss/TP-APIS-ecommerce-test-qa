import pytest


def _primera_variante_con_stock(client) -> dict:
    """Devuelve la primera variante con stock > 0."""
    variantes = client.get("/variantes").json()
    for v in variantes:
        if v.get("stock", 0) > 0:
            return v
    pytest.skip("No hay variantes con stock disponible")


def _crear_carrito(client, usuario_id: int) -> dict:
    resp = client.post("/carritos", json={"usuarioId": usuario_id})
    assert resp.status_code in (200, 201)
    return resp.json()


@pytest.mark.api
class TestCrearCarrito:
    def test_crear_carrito_autenticado_estado_activo(self, user_client):
        user_id = user_client._auth_data["id"]
        carrito = _crear_carrito(user_client, user_id)
        assert carrito["estado"] == "ACTIVO"
        assert carrito["usuarioId"] == user_id

    def test_crear_carrito_sin_auth_devuelve_401(self, client):
        resp = client.post("/carritos", json={"usuarioId": 1})
        assert resp.status_code == 401


@pytest.mark.api
class TestItemsCarrito:
    def test_agregar_item_valido_aparece_en_carrito(self, user_client):
        user_id = user_client._auth_data["id"]
        carrito = _crear_carrito(user_client, user_id)
        variante = _primera_variante_con_stock(user_client)

        resp = user_client.post(
            f"/carritos/{carrito['id']}/items",
            json={"idVariante": variante["id"], "cantidad": 1},
        )
        assert resp.status_code in (200, 201)
        data = resp.json()
        items = data.get("items", [])
        variante_ids = [i["idVariante"] if "idVariante" in i else i.get("varianteId") for i in items]
        assert variante["id"] in variante_ids

    def test_actualizar_cantidad_item(self, user_client):
        user_id = user_client._auth_data["id"]
        carrito = _crear_carrito(user_client, user_id)
        variante = _primera_variante_con_stock(user_client)

        add_resp = user_client.post(
            f"/carritos/{carrito['id']}/items",
            json={"idVariante": variante["id"], "cantidad": 1},
        )
        assert add_resp.status_code in (200, 201)
        items = add_resp.json().get("items", [])
        item_id = items[0]["id"]

        upd_resp = user_client.put(
            f"/carritos/{carrito['id']}/items/{item_id}",
            params={"cantidad": 2},
        )
        assert upd_resp.status_code == 200
        items_upd = upd_resp.json().get("items", [])
        item_upd = next(i for i in items_upd if i["id"] == item_id)
        assert item_upd["cantidad"] == 2

    def test_eliminar_item_del_carrito(self, user_client):
        user_id = user_client._auth_data["id"]
        carrito = _crear_carrito(user_client, user_id)
        variante = _primera_variante_con_stock(user_client)

        add_resp = user_client.post(
            f"/carritos/{carrito['id']}/items",
            json={"idVariante": variante["id"], "cantidad": 1},
        )
        assert add_resp.status_code in (200, 201)
        item_id = add_resp.json()["items"][0]["id"]

        del_resp = user_client.delete(f"/carritos/{carrito['id']}/items/{item_id}")
        assert del_resp.status_code in (200, 204)

        carrito_actual = user_client.get(f"/carritos").json()
        carrito_data = next((c for c in carrito_actual if c["id"] == carrito["id"]), None)
        if carrito_data:
            items = carrito_data.get("items", [])
            assert all(i["id"] != item_id for i in items)


@pytest.mark.api
class TestDescuentoCarrito:
    def test_aplicar_cupon_valido_actualiza_carrito(self, user_client):
        user_id = user_client._auth_data["id"]
        carrito = _crear_carrito(user_client, user_id)
        variante = _primera_variante_con_stock(user_client)

        user_client.post(
            f"/carritos/{carrito['id']}/items",
            json={"idVariante": variante["id"], "cantidad": 1},
        )

        resp = user_client.put(
            f"/carritos/{carrito['id']}/descuento",
            json={"codigo": "OTONO2026"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("descuentoId") is not None or data.get("codigoDescuento") == "OTONO2026"

    def test_aplicar_cupon_invalido_devuelve_error(self, user_client):
        user_id = user_client._auth_data["id"]
        carrito = _crear_carrito(user_client, user_id)

        resp = user_client.put(
            f"/carritos/{carrito['id']}/descuento",
            json={"codigo": "CUPONINEXISTENTE999"},
        )
        assert resp.status_code in (400, 404)

    def test_vaciar_carrito(self, user_client):
        user_id = user_client._auth_data["id"]
        carrito = _crear_carrito(user_client, user_id)
        variante = _primera_variante_con_stock(user_client)

        user_client.post(
            f"/carritos/{carrito['id']}/items",
            json={"idVariante": variante["id"], "cantidad": 1},
        )

        resp = user_client.post(f"/carritos/{carrito['id']}/vaciar")
        assert resp.status_code in (200, 204)
