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


@pytest.mark.api
class TestCheckoutEdgeCases:
    def test_checkout_doble_mismo_carrito_falla(self, new_user_client):
        """Un carrito ya convertido no puede hacer checkout otra vez."""
        user_id = new_user_client._auth_data["id"]
        carrito, _ = _setup_carrito_con_item(new_user_client, user_id)

        r1 = new_user_client.post(f"/carritos/{carrito['id']}/checkout", json=DATOS_ENVIO)
        assert r1.status_code in (200, 201)

        r2 = new_user_client.post(f"/carritos/{carrito['id']}/checkout", json=DATOS_ENVIO)
        assert r2.status_code in (400, 409, 422), (
            f"Segundo checkout debería fallar, obtuvo {r2.status_code}"
        )

    def test_checkout_guarda_datos_envio_en_orden(self, new_user_client):
        """La orden creada debe contener los datos de envío."""
        user_id = new_user_client._auth_data["id"]
        carrito, _ = _setup_carrito_con_item(new_user_client, user_id)

        resp = new_user_client.post(f"/carritos/{carrito['id']}/checkout", json=DATOS_ENVIO)
        assert resp.status_code in (200, 201)
        orden = resp.json()

        # Verificar que la orden tiene los datos de envío
        assert orden.get("nombreDestinatario") == DATOS_ENVIO["nombreDestinatario"]
        assert orden.get("direccion") == DATOS_ENVIO["direccion"]
        assert orden.get("ciudad") == DATOS_ENVIO["ciudad"]
        assert orden.get("metodoPago") == DATOS_ENVIO["metodoPago"]

    def test_checkout_orden_tiene_items_correctos(self, new_user_client):
        """La orden creada debe tener los mismos items del carrito."""
        user_id = new_user_client._auth_data["id"]
        carrito, variante = _setup_carrito_con_item(new_user_client, user_id)

        resp = new_user_client.post(f"/carritos/{carrito['id']}/checkout", json=DATOS_ENVIO)
        assert resp.status_code in (200, 201)
        orden = resp.json()

        # Verificar items via GET /ordenes/{id}/items
        items_resp = new_user_client.get(f"/ordenes/{orden['id']}/items")
        assert items_resp.status_code == 200
        items = items_resp.json()
        assert len(items) > 0, "La orden no tiene items"
        variante_ids = [i["varianteId"] for i in items]
        assert variante["id"] in variante_ids

    def test_checkout_con_cantidad_mayor_a_stock_falla(self, new_user_client):
        """Si la cantidad solicitada excede el stock, checkout debe fallar."""
        user_id = new_user_client._auth_data["id"]

        # Crear carrito
        carrito_resp = new_user_client.post("/carritos", json={"usuarioId": user_id})
        assert carrito_resp.status_code in (200, 201)
        carrito = carrito_resp.json()

        # Buscar variante con stock limitado
        variantes = new_user_client.get("/variantes").json()
        variante = next((v for v in variantes if 0 < v.get("stock", 0) <= 5), None)
        if variante is None:
            pytest.skip("No hay variantes con stock bajo para este test")

        # Agregar cantidad que excede el stock
        add_resp = new_user_client.post(
            f"/carritos/{carrito['id']}/items",
            json={"idVariante": variante["id"], "cantidad": variante["stock"] + 100},
        )
        # Puede fallar al agregar o al hacer checkout
        if add_resp.status_code in (200, 201):
            resp = new_user_client.post(f"/carritos/{carrito['id']}/checkout", json=DATOS_ENVIO)
            assert resp.status_code in (400, 422), (
                f"Checkout con stock insuficiente debería fallar, obtuvo {resp.status_code}"
            )

    def test_checkout_monto_final_positivo(self, new_user_client):
        """El monto final de la orden siempre debe ser positivo."""
        user_id = new_user_client._auth_data["id"]
        carrito, _ = _setup_carrito_con_item(new_user_client, user_id)

        resp = new_user_client.post(f"/carritos/{carrito['id']}/checkout", json=DATOS_ENVIO)
        assert resp.status_code in (200, 201)
        orden = resp.json()
        assert orden["montoFinal"] > 0, "Monto final debe ser positivo"

