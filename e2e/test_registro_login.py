import uuid
import os

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
        page.get_by_label("Email").fill(f"nuevo_{suffix}@test.com")
        page.get_by_label("Nombre").fill("Nuevo")
        page.get_by_label("Apellido").fill("Usuario")
        # Campos de contraseña — buscar por placeholder o name si no hay label
        page.get_by_label("Contraseña").fill("Segura1234!")
        page.get_by_label("Confirmar contraseña").fill("Segura1234!")
        page.get_by_role("button", name="Registrarse").click()
        expect(page).to_have_url(f"{FRONTEND_URL}/", timeout=10_000)

    def test_registro_password_debil_muestra_error_inline(self, page: Page):
        """Contraseña sin mayúscula y sin número — error inline, sin llamada al backend."""
        suffix = uuid.uuid4().hex[:8]
        page.goto(f"{FRONTEND_URL}/registro")
        page.get_by_label("Usuario").fill(f"weak_{suffix}")
        page.get_by_label("Email").fill(f"weak_{suffix}@test.com")
        page.get_by_label("Nombre").fill("Weak")
        page.get_by_label("Apellido").fill("Pass")
        page.get_by_label("Contraseña").fill("debil")  # < 8 chars, sin mayúscula, sin número
        page.get_by_label("Confirmar contraseña").fill("debil")
        page.get_by_role("button", name="Registrarse").click()

        # El error debe mostrarse sin hacer POST al backend
        error_locator = page.locator("text=/contraseña|password|requisito/i").first
        expect(error_locator).to_be_visible(timeout=5_000)
        # La URL no debe cambiar
        expect(page).to_have_url(f"{FRONTEND_URL}/registro", timeout=3_000)

    def test_registro_password_sin_mayuscula_muestra_error(self, page: Page):
        suffix = uuid.uuid4().hex[:8]
        page.goto(f"{FRONTEND_URL}/registro")
        page.get_by_label("Usuario").fill(f"nomay_{suffix}")
        page.get_by_label("Email").fill(f"nomay_{suffix}@test.com")
        page.get_by_label("Nombre").fill("No")
        page.get_by_label("Apellido").fill("Mayuscula")
        page.get_by_label("Contraseña").fill("sinnumero1")  # sin mayúscula
        page.get_by_label("Confirmar contraseña").fill("sinnumero1")
        page.get_by_role("button", name="Registrarse").click()

        error_locator = page.locator("text=/contraseña|password|requisito|mayúscula/i").first
        expect(error_locator).to_be_visible(timeout=5_000)

    def test_registro_passwords_no_coinciden_muestra_error(self, page: Page):
        suffix = uuid.uuid4().hex[:8]
        page.goto(f"{FRONTEND_URL}/registro")
        page.get_by_label("Usuario").fill(f"mismatch_{suffix}")
        page.get_by_label("Email").fill(f"mismatch_{suffix}@test.com")
        page.get_by_label("Nombre").fill("Mis")
        page.get_by_label("Apellido").fill("Match")
        page.get_by_label("Contraseña").fill("Segura1234!")
        page.get_by_label("Confirmar contraseña").fill("OtraPassword1!")
        page.get_by_role("button", name="Registrarse").click()

        expect(page.locator("text=Las contraseñas no coinciden")).to_be_visible(timeout=5_000)


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
        expect(page).to_have_url(f"{FRONTEND_URL}/admin/dashboard", timeout=10_000)

    def test_login_credenciales_incorrectas_muestra_error(self, page: Page):
        page.goto(f"{FRONTEND_URL}/login")
        page.get_by_label("Usuario").fill("usuarioinexistente")
        page.get_by_label("Contraseña").fill("passwordincorrecto")
        page.get_by_role("button", name="Iniciar sesión").click()

        error_locator = page.locator("text=/credenciales|inválid|incorrecto|error/i").first
        expect(error_locator).to_be_visible(timeout=8_000)

    def test_logout_muestra_iniciar_sesion_en_navbar(self, logged_in_page: Page):
        page = logged_in_page
        # Abrir menú de perfil y hacer logout
        page.get_by_role("button", name=/perfil|mi cuenta|usuario/i).click()
        page.get_by_role("menuitem", name=/cerrar sesión|logout|salir/i).click()

        navbar = page.locator("nav")
        expect(navbar.get_by_text("Iniciar sesión")).to_be_visible(timeout=8_000)
