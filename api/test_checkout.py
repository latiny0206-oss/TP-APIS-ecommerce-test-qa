import pytest


DATOS_ENVIO = {
    "nombreDestinatario": "Juan Perez",
    "direccion": "Av. Siempre Viva 742",
    "ciudad": "Buenos Aires",
    "provincia": "Buenos Aires",
    "codigoPostal": "1414",
    "telefono": "1155559999",
    "metodoPago": "TRANSFERENCIA",
}


def _primera_variante_con_stock(client) -> dict:
    variantes = client.get("/variantes").json()
    for v in variantes:
        if v.get("stock", 0) > 0:
            return v
    pytest.skip("No hay variantes con stock disponible")


def _setup_carrito_con_item(client, usuario_id: int) -> tuple[dict, dict]:
    """Crea carrito y agrega un item. Devuelve (carrito, variante)."""
    carrito_resp = client.post("/carritos", json={"usuarioId": usuario_id})
    assert carrito_resp.status_code in (200, 201)
    carrito = carrito_resp.json()

    variante = _primera_variante_con_stock(client)
    add_resp = client.post(
        f"/carritos/{carrito['id']}/items",
        json={"idVariante": variante["id"], "cantidad": 1},
    )
    assert add_resp.status_code in (200, 201)
    return carrito, variante


@pytest.mark.api
class TestCheckout:
    def test_checkout_carrito_vacio_devuelve_error(self, new_user_client):
        user_id = new_user_client._auth_data["id"]
        carrito_resp = new_user_client.post("/carritos", json={"usuarioId": user_id})
        assert carrito_resp.status_code in (200, 201)
        carrito_id = carrito_resp.json()["id"]

        # Vaciar por si tiene items (no debería, recién creado)
        resp = new_user_client.post(f"/carritos/{carrito_id}/checkout", json=DATOS_ENVIO)
        # Carrito sin items debe devolver error de negocio
        assert resp.status_code in (400, 422)

    def test_checkout_completo_devuelve_orden_pendiente(self, new_user_client):
        user_id = new_user_client._auth_data["id"]
        carrito, _ = _setup_carrito_con_item(new_user_client, user_id)

        resp = new_user_client.post(f"/carritos/{carrito['id']}/checkout", json=DATOS_ENVIO)
        assert resp.status_code in (200, 201)
        orden = resp.json()
        assert orden["estado"] == "PENDIENTE"
        assert orden["montoFinal"] > 0
        assert "id" in orden

    def test_checkout_descuenta_stock_variante(self, new_user_client):
        user_id = new_user_client._auth_data["id"]
        carrito, variante = _setup_carrito_con_item(new_user_client, user_id)

        stock_antes = variante["stock"]

        resp = new_user_client.post(f"/carritos/{carrito['id']}/checkout", json=DATOS_ENVIO)
        assert resp.status_code in (200, 201)

        variante_actualizada = new_user_client.get(f"/variantes/{variante['id']}").json()
        assert variante_actualizada["stock"] == stock_antes - 1

    def test_checkout_con_cupon_aplica_descuento_en_monto(self, new_user_client):
        user_id = new_user_client._auth_data["id"]
        carrito, variante = _setup_carrito_con_item(new_user_client, user_id)

        # Obtener total sin descuento
        total_resp = new_user_client.get(f"/carritos/{carrito['id']}/total")
        total_sin_descuento = float(total_resp.json()) if total_resp.status_code == 200 else variante["precio"]

        # Aplicar cupón 15%
        cup_resp = new_user_client.put(
            f"/carritos/{carrito['id']}/descuento",
            json={"codigo": "OTONO2026"},
        )
        assert cup_resp.status_code == 200

        resp = new_user_client.post(f"/carritos/{carrito['id']}/checkout", json=DATOS_ENVIO)
        assert resp.status_code in (200, 201)
        orden = resp.json()

        monto_esperado = total_sin_descuento * 0.85
        assert orden["montoFinal"] == pytest.approx(monto_esperado, rel=0.01)

    def test_checkout_carrito_queda_convertido(self, new_user_client):
        user_id = new_user_client._auth_data["id"]
        carrito, _ = _setup_carrito_con_item(new_user_client, user_id)

        resp = new_user_client.post(f"/carritos/{carrito['id']}/checkout", json=DATOS_ENVIO)
        assert resp.status_code in (200, 201)

        # Verificar estado del carrito
        carritos = new_user_client.get("/carritos").json()
        carrito_data = next((c for c in carritos if c["id"] == carrito["id"]), None)
        if carrito_data:
            assert carrito_data["estado"] == "CONVERTIDO"
