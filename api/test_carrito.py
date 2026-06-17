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


def _get_carrito(client, carrito_id: int) -> dict | None:
    """Obtiene el carrito actual desde GET /carritos filtrando por id."""
    carts = client.get("/carritos").json()
    return next((c for c in carts if c["id"] == carrito_id), None)


@pytest.mark.api
class TestCrearCarrito:
    def test_crear_carrito_autenticado_estado_activo(self, new_user_client):
        user_id = new_user_client._auth_data["id"]
        carrito = _crear_carrito(new_user_client, user_id)
        # El carrito recién creado puede estar en estado ACTIVO o VACIO según el backend
        assert carrito["estado"] in ("ACTIVO", "VACIO")
        assert carrito["usuarioId"] == user_id

    def test_crear_carrito_sin_auth_devuelve_401(self, client):
        resp = client.post("/carritos", json={"usuarioId": 1})
        assert resp.status_code in (401, 403)


@pytest.mark.api
class TestItemsCarrito:
    def test_agregar_item_valido_aparece_en_carrito(self, new_user_client):
        user_id = new_user_client._auth_data["id"]
        carrito = _crear_carrito(new_user_client, user_id)
        variante = _primera_variante_con_stock(new_user_client)

        resp = new_user_client.post(
            f"/carritos/{carrito['id']}/items",
            json={"idVariante": variante["id"], "cantidad": 1},
        )
        assert resp.status_code in (200, 201)

        # Verificar que el item aparece en el carrito via GET
        carrito_data = _get_carrito(new_user_client, carrito["id"])
        assert carrito_data is not None
        items = carrito_data.get("items", [])
        variante_ids = [i.get("idVariante") or i.get("varianteId") for i in items]
        assert variante["id"] in variante_ids

    def test_actualizar_cantidad_item(self, new_user_client):
        user_id = new_user_client._auth_data["id"]
        carrito = _crear_carrito(new_user_client, user_id)
        variante = _primera_variante_con_stock(new_user_client)

        add_resp = new_user_client.post(
            f"/carritos/{carrito['id']}/items",
            json={"idVariante": variante["id"], "cantidad": 1},
        )
        assert add_resp.status_code in (200, 201)

        # Obtener el item_id desde el carrito via GET
        carrito_data = _get_carrito(new_user_client, carrito["id"])
        assert carrito_data is not None
        items = carrito_data.get("items", [])
        assert len(items) > 0, "El carrito debería tener al menos un item"
        item_id = items[0]["id"]

        upd_resp = new_user_client.put(
            f"/carritos/{carrito['id']}/items/{item_id}",
            params={"cantidad": 2},
        )
        assert upd_resp.status_code == 200

        # Verificar la cantidad actualizada via GET
        carrito_upd = _get_carrito(new_user_client, carrito["id"])
        items_upd = carrito_upd.get("items", []) if carrito_upd else []
        item_upd = next(i for i in items_upd if i["id"] == item_id)
        assert item_upd["cantidad"] == 2

    def test_eliminar_item_del_carrito(self, new_user_client):
        user_id = new_user_client._auth_data["id"]
        carrito = _crear_carrito(new_user_client, user_id)
        variante = _primera_variante_con_stock(new_user_client)

        add_resp = new_user_client.post(
            f"/carritos/{carrito['id']}/items",
            json={"idVariante": variante["id"], "cantidad": 1},
        )
        assert add_resp.status_code in (200, 201)

        # Obtener el item_id desde el carrito via GET
        carrito_data = _get_carrito(new_user_client, carrito["id"])
        assert carrito_data is not None
        items = carrito_data.get("items", [])
        assert len(items) > 0, "El carrito debería tener al menos un item"
        item_id = items[0]["id"]

        del_resp = new_user_client.delete(f"/carritos/{carrito['id']}/items/{item_id}")
        assert del_resp.status_code in (200, 204)

        carrito_final = _get_carrito(new_user_client, carrito["id"])
        if carrito_final:
            items_final = carrito_final.get("items", [])
            assert all(i["id"] != item_id for i in items_final)


@pytest.mark.api
class TestDescuentoCarrito:
    def test_aplicar_cupon_valido_actualiza_carrito(self, new_user_client):
        user_id = new_user_client._auth_data["id"]
        carrito = _crear_carrito(new_user_client, user_id)
        variante = _primera_variante_con_stock(new_user_client)

        new_user_client.post(
            f"/carritos/{carrito['id']}/items",
            json={"idVariante": variante["id"], "cantidad": 1},
        )

        resp = new_user_client.put(
            f"/carritos/{carrito['id']}/descuento",
            json={"codigo": "OTONO2026"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("descuentoId") is not None or data.get("codigoDescuento") == "OTONO2026"

    def test_aplicar_cupon_invalido_devuelve_error(self, new_user_client):
        user_id = new_user_client._auth_data["id"]
        carrito = _crear_carrito(new_user_client, user_id)

        resp = new_user_client.put(
            f"/carritos/{carrito['id']}/descuento",
            json={"codigo": "CUPONINEXISTENTE999"},
        )
        assert resp.status_code in (400, 404)

    def test_vaciar_carrito(self, new_user_client):
        user_id = new_user_client._auth_data["id"]
        carrito = _crear_carrito(new_user_client, user_id)
        variante = _primera_variante_con_stock(new_user_client)

        new_user_client.post(
            f"/carritos/{carrito['id']}/items",
            json={"idVariante": variante["id"], "cantidad": 1},
        )

        resp = new_user_client.post(f"/carritos/{carrito['id']}/vaciar")
        assert resp.status_code in (200, 204)
