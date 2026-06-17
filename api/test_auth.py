import uuid

import pytest


@pytest.mark.api
class TestLogin:
    def test_login_correcto_devuelve_token_y_campos(self, client):
        resp = client.post("/auth/login", json={"username": "juanperez", "password": "user123"})
        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data
        assert data["token"]
        assert "id" in data
        assert data["username"] == "juanperez"
        assert "rol" in data

    def test_login_admin_rol_correcto(self, client):
        resp = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
        assert resp.status_code == 200
        assert resp.json()["rol"] == "ADMIN"

    def test_login_cliente_rol_correcto(self, client):
        resp = client.post("/auth/login", json={"username": "juanperez", "password": "user123"})
        assert resp.status_code == 200
        assert resp.json()["rol"] == "CLIENTE"

    def test_login_password_incorrecto_devuelve_401(self, client):
        resp = client.post("/auth/login", json={"username": "juanperez", "password": "wrongpassword"})
        assert resp.status_code == 401

    def test_login_usuario_inexistente_devuelve_401(self, client):
        resp = client.post("/auth/login", json={"username": "noexiste", "password": "cualquier"})
        assert resp.status_code == 401

    def test_login_body_vacio_devuelve_error(self, client):
        resp = client.post("/auth/login", json={})
        assert resp.status_code in (400, 401)


@pytest.mark.api
class TestRegistro:
    def test_registro_valido_devuelve_201_y_token(self, client):
        suffix = uuid.uuid4().hex[:8]
        payload = {
            "username": f"nuevo_{suffix}",
            "email": f"nuevo_{suffix}@test.com",
            "password": "Segura1234!",
            "nombre": "Nuevo",
            "apellido": "Usuario",
        }
        resp = client.post("/auth/register", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert "token" in data
        assert data["token"]
        assert data["username"] == payload["username"]

    def test_registro_devuelve_campos_requeridos(self, client):
        suffix = uuid.uuid4().hex[:8]
        payload = {
            "username": f"check_{suffix}",
            "email": f"check_{suffix}@test.com",
            "password": "Segura1234!",
            "nombre": "Check",
            "apellido": "Fields",
        }
        resp = client.post("/auth/register", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        for campo in ("id", "token", "username", "nombre", "email", "rol"):
            assert campo in data, f"Falta el campo '{campo}' en la respuesta de registro"

    def test_registro_username_duplicado_devuelve_error(self, client):
        # juanperez ya existe en el seed
        payload = {
            "username": "juanperez",
            "email": "otro@test.com",
            "password": "Segura1234!",
            "nombre": "Juan",
            "apellido": "Perez",
        }
        resp = client.post("/auth/register", json=payload)
        assert resp.status_code in (400, 409)

    def test_registro_email_duplicado_devuelve_error(self, client):
        # Primer registro
        suffix = uuid.uuid4().hex[:8]
        email = f"dup_{suffix}@test.com"
        payload = {
            "username": f"dup1_{suffix}",
            "email": email,
            "password": "Segura1234!",
            "nombre": "Dup",
            "apellido": "One",
        }
        r1 = client.post("/auth/register", json=payload)
        assert r1.status_code == 201

        # Segundo registro con el mismo email
        payload2 = {**payload, "username": f"dup2_{suffix}"}
        r2 = client.post("/auth/register", json=payload2)
        assert r2.status_code in (400, 409)


@pytest.mark.api
class TestEndpointProtegido:
    def test_acceso_sin_token_devuelve_401(self, client):
        resp = client.get("/carritos")
        assert resp.status_code in (401, 403)

    def test_acceso_con_token_invalido_devuelve_401(self, client):
        resp = client.get("/carritos", headers={"Authorization": "Bearer tokeninvalido"})
        assert resp.status_code in (401, 403)
