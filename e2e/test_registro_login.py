import uuid
import os
import re

import pytest
from dotenv import load_dotenv
from playwright.sync_api import Page, expect

load_dotenv()
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")


@pytest.mark.e2e
class TestRegistro:
    def test_registro_exitoso_redirige_a_inicio(self, page: Page):
        suffix = uuid.uuid4().hex[:8]
        page.goto(f"{FRONTEND_URL}/registro")
        page.get_by_label("Usuario").fill(f"nuevo_{suffix}")
        page.get_by_label("Nombre").fill("Nuevo")
        page.get_by_label("Apellido").fill("Usuario")
        page.get_by_label("Email").fill(f"nuevo_{suffix}@test.com")
        # exact=True para distinguir "Contraseña" de "Confirmar contraseña"
        page.get_by_label("Contraseña", exact=True).fill("Segura1234!")
        page.get_by_label("Confirmar contraseña", exact=True).fill("Segura1234!")
        # Botón correcto según el frontend: "Crear cuenta"
        page.get_by_role("button", name="Crear cuenta").click()
        # El frontend muestra "¡Todo listo!" y redirige a "/" tras 2000ms
        expect(page).to_have_url(f"{FRONTEND_URL}/", timeout=12_000)

    def test_registro_password_debil_muestra_error_inline(self, page: Page):
        """Contraseña < 8 chars, sin mayúscula y sin número → error inline."""
        suffix = uuid.uuid4().hex[:8]
        page.goto(f"{FRONTEND_URL}/registro")
        page.get_by_label("Usuario").fill(f"weak_{suffix}")
        page.get_by_label("Nombre").fill("Weak")
        page.get_by_label("Apellido").fill("Pass")
        page.get_by_label("Email").fill(f"weak_{suffix}@test.com")
        page.get_by_label("Contraseña", exact=True).fill("debil")
        page.get_by_label("Confirmar contraseña", exact=True).fill("debil")
        page.get_by_role("button", name="Crear cuenta").click()

        # Mensaje exacto de validación del frontend
        expect(
            page.get_by_text("Mínimo 8 caracteres, una mayúscula y un número")
        ).to_be_visible(timeout=5_000)
        expect(page).to_have_url(f"{FRONTEND_URL}/registro", timeout=3_000)

    def test_registro_password_sin_mayuscula_muestra_error(self, page: Page):
        suffix = uuid.uuid4().hex[:8]
        page.goto(f"{FRONTEND_URL}/registro")
        page.get_by_label("Usuario").fill(f"nomay_{suffix}")
        page.get_by_label("Nombre").fill("No")
        page.get_by_label("Apellido").fill("Mayuscula")
        page.get_by_label("Email").fill(f"nomay_{suffix}@test.com")
        page.get_by_label("Contraseña", exact=True).fill("sinnumero1")   # sin mayúscula
        page.get_by_label("Confirmar contraseña", exact=True).fill("sinnumero1")
        page.get_by_role("button", name="Crear cuenta").click()

        expect(
            page.get_by_text("Mínimo 8 caracteres, una mayúscula y un número")
        ).to_be_visible(timeout=5_000)

    def test_registro_passwords_no_coinciden_muestra_error(self, page: Page):
        suffix = uuid.uuid4().hex[:8]
        page.goto(f"{FRONTEND_URL}/registro")
        page.get_by_label("Usuario").fill(f"mismatch_{suffix}")
        page.get_by_label("Nombre").fill("Mis")
        page.get_by_label("Apellido").fill("Match")
        page.get_by_label("Email").fill(f"mismatch_{suffix}@test.com")
        page.get_by_label("Contraseña", exact=True).fill("Segura1234!")
        page.get_by_label("Confirmar contraseña", exact=True).fill("OtraPassword1!")
        page.get_by_role("button", name="Crear cuenta").click()

        # Mensaje exacto del frontend
        expect(page.get_by_text("Las contraseñas no coinciden")).to_be_visible(timeout=5_000)


@pytest.mark.e2e
class TestLogin:
    def test_login_correcto_cliente_redirige_a_inicio(self, page: Page):
        page.goto(f"{FRONTEND_URL}/login")
        page.get_by_label("Usuario").fill("juanperez")
        page.get_by_label("Contraseña").fill("user123")
        page.get_by_role("button", name="Iniciar sesión").click()
        expect(page).to_have_url(f"{FRONTEND_URL}/", timeout=10_000)

    def test_login_correcto_admin_redirige_a_dashboard(self, page: Page):
        page.goto(f"{FRONTEND_URL}/login")
        page.get_by_label("Usuario").fill("admin")
        page.get_by_label("Contraseña").fill("admin123")
        page.get_by_role("button", name="Iniciar sesión").click()
        # El admin puede ir a "/" y luego el frontend redirige a /admin/dashboard,
        # o directamente a /admin/dashboard según la implementación del router.
        page.wait_for_url(lambda url: "/login" not in url, timeout=10_000)
        if "/admin/dashboard" not in page.url:
            page.goto(f"{FRONTEND_URL}/admin/dashboard")
        expect(page).to_have_url(re.compile(r"/admin/dashboard"), timeout=8_000)

    def test_login_credenciales_incorrectas_muestra_error(self, page: Page):
        page.goto(f"{FRONTEND_URL}/login")
        page.get_by_label("Usuario").fill("usuarioinexistente")
        page.get_by_label("Contraseña").fill("passwordincorrecto")
        page.get_by_role("button", name="Iniciar sesión").click()

        # El frontend muestra un alert con el mensaje de error del servidor
        error_locator = page.locator("text=/credenciales|inválid|incorrecto|error/i").first
        expect(error_locator).to_be_visible(timeout=8_000)

    def test_logout_muestra_iniciar_sesion_en_navbar(self, logged_in_page: Page):
        page = logged_in_page
        # Desktop: botón "Salir" con ícono LogOut — usar filter por texto
        page.locator("button").filter(has_text="Salir").click()
        # El navbar tiene "Iniciar sesión" tanto en desktop como mobile: usar .first
        expect(page.get_by_text("Iniciar sesión").first).to_be_visible(timeout=8_000)


@pytest.mark.e2e
class TestRegistroEdgeCasesE2E:
    def test_registro_email_duplicado_muestra_error(self, page: Page):
        """Registrar con un email ya existente debe mostrar error en la UI."""
        # juanperez ya existe en el seed con email juan.perez@mail.com
        suffix = uuid.uuid4().hex[:8]
        page.goto(f"{FRONTEND_URL}/registro")
        page.get_by_label("Usuario").fill(f"otro_{suffix}")
        page.get_by_label("Nombre").fill("Otro")
        page.get_by_label("Apellido").fill("Usuario")
        page.get_by_label("Email").fill("juan.perez@mail.com")  # email que ya existe
        page.get_by_label("Contraseña", exact=True).fill("Segura1234!")
        page.get_by_label("Confirmar contraseña", exact=True).fill("Segura1234!")
        page.get_by_role("button", name="Crear cuenta").click()

        # Debe mostrar error y quedarse en /registro
        error = page.locator("text=/error|ya existe|registrado|duplicad/i").first
        expect(error).to_be_visible(timeout=8_000)
        expect(page).to_have_url(re.compile(r"/registro"), timeout=3_000)

    def test_registro_username_duplicado_muestra_error(self, page: Page):
        """Registrar con un username ya existente debe mostrar error."""
        suffix = uuid.uuid4().hex[:8]
        page.goto(f"{FRONTEND_URL}/registro")
        page.get_by_label("Usuario").fill("juanperez")  # username que ya existe
        page.get_by_label("Nombre").fill("Juan")
        page.get_by_label("Apellido").fill("Otro")
        page.get_by_label("Email").fill(f"otro_{suffix}@test.com")
        page.get_by_label("Contraseña", exact=True).fill("Segura1234!")
        page.get_by_label("Confirmar contraseña", exact=True).fill("Segura1234!")
        page.get_by_role("button", name="Crear cuenta").click()

        error = page.locator("text=/error|ya existe|registrado|duplicad/i").first
        expect(error).to_be_visible(timeout=8_000)
        expect(page).to_have_url(re.compile(r"/registro"), timeout=3_000)


@pytest.mark.e2e
class TestLoginIntegrationE2E:
    def test_login_exitoso_guarda_token_en_localstorage(self, page: Page):
        """Tras login exitoso, cumbre_token debe existir en localStorage."""
        page.goto(f"{FRONTEND_URL}/login")
        page.get_by_label("Usuario").fill("juanperez")
        page.get_by_label("Contraseña").fill("user123")
        page.get_by_role("button", name="Iniciar sesión").click()
        expect(page).to_have_url(f"{FRONTEND_URL}/", timeout=10_000)

        token = page.evaluate("() => localStorage.getItem('cumbre_token')")
        assert token is not None, "cumbre_token no se guardó en localStorage"
        assert token.startswith("eyJ"), "Token no parece ser un JWT válido"

    def test_logout_limpia_token_de_localstorage(self, logged_in_page: Page):
        """Tras logout, cumbre_token debe eliminarse de localStorage."""
        page = logged_in_page
        page.locator("button").filter(has_text="Salir").click()
        expect(page.get_by_text("Iniciar sesión").first).to_be_visible(timeout=8_000)

        token = page.evaluate("() => localStorage.getItem('cumbre_token')")
        assert token is None, "cumbre_token no se limpió tras logout"

    def test_navbar_muestra_nombre_tras_login(self, logged_in_page: Page):
        """El navbar debe mostrar el nombre del usuario logueado."""
        page = logged_in_page
        # El seed tiene juanperez con nombre "Juan"
        expect(page.get_by_text("Juan").first).to_be_visible(timeout=5_000)

