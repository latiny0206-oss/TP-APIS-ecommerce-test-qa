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


@pytest.mark.api
class TestRegistroEdgeCases:
    def test_registro_caracteres_especiales_nombre_preservados(self, client):
        """Nombres con acentos y ñ deben preservarse en la respuesta."""
        suffix = uuid.uuid4().hex[:8]
        payload = {
            "username": f"jose_{suffix}",
            "email": f"jose_{suffix}@test.com",
            "password": "Segura1234!",
            "nombre": "José María",
            "apellido": "García Pérez",
        }
        resp = client.post("/auth/register", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["nombre"] == "José María", "Caracteres especiales en nombre no preservados"

    def test_registro_no_devuelve_password_en_response(self, client):
        """La respuesta de registro NO debe incluir el password."""
        suffix = uuid.uuid4().hex[:8]
        payload = {
            "username": f"nopwd_{suffix}",
            "email": f"nopwd_{suffix}@test.com",
            "password": "Segura1234!",
            "nombre": "NoPwd",
            "apellido": "Test",
        }
        resp = client.post("/auth/register", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert "password" not in data, "Response contiene password — falla de seguridad"

    def test_registro_asigna_rol_cliente_no_admin(self, client):
        """Un registro normal debe asignar rol CLIENTE, nunca ADMIN."""
        suffix = uuid.uuid4().hex[:8]
        payload = {
            "username": f"rol_{suffix}",
            "email": f"rol_{suffix}@test.com",
            "password": "Segura1234!",
            "nombre": "Rol",
            "apellido": "Check",
        }
        resp = client.post("/auth/register", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["rol"] == "CLIENTE", f"Rol esperado CLIENTE, obtenido {data['rol']}"


@pytest.mark.api
class TestJWTValidation:
    def test_token_jwt_tiene_estructura_valida(self, client):
        """El token JWT debe tener 3 partes separadas por '.'."""
        import base64
        import json

        resp = client.post("/auth/login", json={"username": "juanperez", "password": "user123"})
        assert resp.status_code == 200
        token = resp.json()["token"]

        parts = token.split(".")
        assert len(parts) == 3, f"JWT debe tener 3 partes, tiene {len(parts)}"

        # Decodificar payload (con padding)
        payload_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
        payload = json.loads(base64.b64decode(payload_b64))

        # Verificar que tiene campo 'sub' (subject) y 'exp' (expiration)
        assert "sub" in payload, "JWT payload no contiene 'sub'"
        assert "exp" in payload, "JWT payload no contiene 'exp'"

    def test_token_jwt_expiracion_en_el_futuro(self, client):
        """El campo 'exp' del JWT debe ser una fecha futura."""
        import base64
        import json
        import time

        resp = client.post("/auth/login", json={"username": "juanperez", "password": "user123"})
        assert resp.status_code == 200
        token = resp.json()["token"]

        payload_b64 = token.split(".")[1] + "=" * (4 - len(token.split(".")[1]) % 4)
        payload = json.loads(base64.b64decode(payload_b64))

        now = int(time.time())
        assert payload["exp"] > now, "Token JWT ya expiró al momento de crearlo"

    def test_peticion_autenticada_con_token_funciona(self, client):
        """Tras login, el token debe permitir acceder a endpoints protegidos."""
        resp = client.post("/auth/login", json={"username": "juanperez", "password": "user123"})
        assert resp.status_code == 200
        token = resp.json()["token"]

        # Acceder a endpoint protegido
        resp2 = client.get("/carritos", headers={"Authorization": f"Bearer {token}"})
        assert resp2.status_code == 200


@pytest.mark.api
class TestLoginSecurity:
    def test_error_login_password_y_usuario_inexistente_son_iguales(self, client):
        """El error de password incorrecto y usuario inexistente deben ser idénticos
        para no filtrar información sobre qué usuarios existen."""
        r1 = client.post("/auth/login", json={"username": "juanperez", "password": "WrongPass"})
        r2 = client.post("/auth/login", json={"username": "noexiste_xyz", "password": "cualquier"})
        assert r1.status_code == r2.status_code == 401, (
            f"Ambos deben devolver 401, obtuve {r1.status_code} y {r2.status_code}"
        )
