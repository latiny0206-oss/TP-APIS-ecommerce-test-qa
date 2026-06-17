import uuid

import pytest


@pytest.mark.api
class TestListaProductos:
    def test_get_productos_devuelve_lista_no_vacia(self, client):
        resp = client.get("/productos")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_cada_producto_tiene_campos_requeridos(self, client):
        resp = client.get("/productos")
        assert resp.status_code == 200
        for producto in resp.json():
            for campo in ("id", "nombre", "precioBase", "marcaNombre", "categoriaNombre", "estado"):
                assert campo in producto, f"Falta '{campo}' en producto id={producto.get('id')}"

    def test_lista_solo_contiene_activos(self, client):
        resp = client.get("/productos")
        assert resp.status_code == 200
        for producto in resp.json():
            assert producto["estado"] == "ACTIVO"


@pytest.mark.api
class TestDetalleProducto:
    def test_get_producto_por_id_valido(self, client):
        productos = client.get("/productos").json()
        assert productos, "No hay productos en el seed"
        producto_id = productos[0]["id"]
        resp = client.get(f"/productos/{producto_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == producto_id

    def test_get_producto_id_inexistente_devuelve_404(self, client):
        resp = client.get("/productos/999999")
        assert resp.status_code == 404

    def test_get_productos_por_categoria(self, client):
        resp = client.get("/productos/categoria/1")  # Calzado
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_productos_por_marca(self, client):
        resp = client.get("/productos/marca/1")  # Columbia
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


@pytest.mark.api
class TestProductosPorEstado:
    def test_get_estado_sin_token_devuelve_401(self, client):
        resp = client.get("/productos/estado/ACTIVO")
        assert resp.status_code == 401

    def test_get_estado_activo_como_admin(self, admin_client):
        resp = admin_client.get("/productos/estado/ACTIVO")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_estado_pausado_como_admin(self, admin_client):
        resp = admin_client.get("/productos/estado/PAUSADO")
        assert resp.status_code == 200

    def test_get_estado_eliminado_como_admin(self, admin_client):
        resp = admin_client.get("/productos/estado/ELIMINADO")
        assert resp.status_code == 200


@pytest.mark.api
class TestCrearProducto:
    def _payload(self):
        suffix = uuid.uuid4().hex[:6]
        return {
            "nombre": f"Producto Test {suffix}",
            "descripcion": "Descripción de prueba",
            "marcaId": 1,
            "categoriaId": 1,
            "precioBase": 15000.0,
            "estado": "ACTIVO",
        }

    def test_crear_producto_como_admin_devuelve_201(self, admin_client):
        resp = admin_client.post("/productos", json=self._payload())
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert data["estado"] == "ACTIVO"

    def test_producto_creado_aparece_en_lista(self, admin_client, client):
        payload = self._payload()
        resp = admin_client.post("/productos", json=payload)
        assert resp.status_code == 201
        nuevo_id = resp.json()["id"]

        lista = client.get("/productos").json()
        ids = [p["id"] for p in lista]
        assert nuevo_id in ids

    def test_crear_producto_como_cliente_devuelve_403(self, user_client):
        resp = user_client.post("/productos", json=self._payload())
        assert resp.status_code == 403

    def test_crear_producto_sin_auth_devuelve_401(self, client):
        resp = client.post("/productos", json=self._payload())
        assert resp.status_code == 401


@pytest.mark.api
class TestActualizarEliminarProducto:
    def _crear_producto(self, admin_client):
        suffix = uuid.uuid4().hex[:6]
        payload = {
            "nombre": f"Prod Upd {suffix}",
            "descripcion": "Para actualizar",
            "marcaId": 2,
            "categoriaId": 2,
            "precioBase": 20000.0,
            "estado": "ACTIVO",
        }
        resp = admin_client.post("/productos", json=payload)
        assert resp.status_code == 201
        return resp.json()

    def test_actualizar_producto_como_admin(self, admin_client):
        producto = self._crear_producto(admin_client)
        pid = producto["id"]
        update = {**producto, "precioBase": 25000.0, "nombre": producto["nombre"] + " updated"}
        resp = admin_client.put(f"/productos/{pid}", json=update)
        assert resp.status_code == 200
        assert resp.json()["precioBase"] == 25000.0

    def test_eliminar_producto_como_admin(self, admin_client):
        producto = self._crear_producto(admin_client)
        pid = producto["id"]
        resp = admin_client.delete(f"/productos/{pid}")
        assert resp.status_code in (200, 204)

        # debe aparecer como ELIMINADO, no en la lista pública
        lista_publica = admin_client.get("/productos").json()
        ids_publicos = [p["id"] for p in lista_publica]
        assert pid not in ids_publicos

    def test_actualizar_producto_como_cliente_devuelve_403(self, user_client, admin_client):
        producto = self._crear_producto(admin_client)
        pid = producto["id"]
        resp = user_client.put(f"/productos/{pid}", json={**producto, "precioBase": 1.0})
        assert resp.status_code == 403
