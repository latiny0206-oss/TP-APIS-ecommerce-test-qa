import pytest


@pytest.mark.api
class TestAdminDashboard:
    def test_dashboard_sin_auth_devuelve_401(self, client):
        resp = client.get("/admin/dashboard")
        assert resp.status_code == 401

    def test_dashboard_como_cliente_devuelve_403(self, user_client):
        resp = user_client.get("/admin/dashboard")
        assert resp.status_code == 403

    def test_dashboard_como_admin_devuelve_200(self, admin_client):
        resp = admin_client.get("/admin/dashboard")
        assert resp.status_code == 200

    def test_dashboard_contiene_todos_los_campos_requeridos(self, admin_client):
        resp = admin_client.get("/admin/dashboard")
        assert resp.status_code == 200
        data = resp.json()
        campos_requeridos = (
            "productosActivos",
            "ordenesPendientes",
            "descuentosActivos",
            "clientesRegistrados",
            "ventasTotales",
            "ordenesRecientes",
        )
        for campo in campos_requeridos:
            assert campo in data, f"Falta el campo '{campo}' en el dashboard"

    def test_campos_numericos_son_no_negativos(self, admin_client):
        resp = admin_client.get("/admin/dashboard")
        assert resp.status_code == 200
        data = resp.json()
        campos_numericos = (
            "productosActivos",
            "ordenesPendientes",
            "descuentosActivos",
            "clientesRegistrados",
            "ventasTotales",
        )
        for campo in campos_numericos:
            assert data[campo] >= 0, f"Campo '{campo}' es negativo: {data[campo]}"

    def test_ordenes_recientes_es_una_lista(self, admin_client):
        resp = admin_client.get("/admin/dashboard")
        assert resp.status_code == 200
        assert isinstance(resp.json()["ordenesRecientes"], list)

    def test_productos_activos_mayor_cero(self, admin_client):
        resp = admin_client.get("/admin/dashboard")
        assert resp.status_code == 200
        # El seed debe tener al menos 1 producto activo
        assert resp.json()["productosActivos"] > 0


@pytest.mark.api
class TestAdminCategoriasMarcas:
    def test_get_categorias_publico(self, client):
        resp = client.get("/categorias")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 4

    def test_categorias_tienen_campos_correctos(self, client):
        resp = client.get("/categorias")
        for cat in resp.json():
            for campo in ("id", "nombre"):
                assert campo in cat

    def test_get_marcas_publico(self, client):
        resp = client.get("/marcas")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 5

    def test_marcas_tienen_campos_correctos(self, client):
        resp = client.get("/marcas")
        for marca in resp.json():
            for campo in ("id", "nombre"):
                assert campo in marca


@pytest.mark.api
class TestContacto:
    def test_post_contacto_publico(self, client):
        payload = {
            "nombre": "Test Tester",
            "email": "test@test.com",
            "asunto": "Consulta de prueba",
            "mensaje": "Este es un mensaje de prueba generado por el test suite.",
        }
        resp = client.post("/contacto", json=payload)
        assert resp.status_code in (200, 201)

    def test_get_contacto_sin_auth_devuelve_401_o_403(self, client):
        resp = client.get("/contacto")
        assert resp.status_code in (401, 403)

    def test_get_contacto_como_admin(self, admin_client):
        resp = admin_client.get("/contacto")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
