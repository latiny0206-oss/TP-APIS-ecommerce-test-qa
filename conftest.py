import os
import uuid

import httpx
import pytest
from dotenv import load_dotenv
from playwright.sync_api import Page, expect

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8080/api")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
USER_USERNAME = os.getenv("USER_USERNAME", "juanperez")
USER_PASSWORD = os.getenv("USER_PASSWORD", "user123")


# ---------------------------------------------------------------------------
# HTTP clients
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    """httpx.Client anónimo apuntando al backend."""
    with httpx.Client(base_url=BACKEND_URL, timeout=10) as c:
        yield c


def _login(base_url: str, username: str, password: str) -> httpx.Client:
    resp = httpx.post(f"{base_url}/auth/login", json={"username": username, "password": password}, timeout=10)
    resp.raise_for_status()
    token = resp.json()["token"]
    client = httpx.Client(base_url=base_url, timeout=10, headers={"Authorization": f"Bearer {token}"})
    client._auth_data = resp.json()  # type: ignore[attr-defined]
    return client


@pytest.fixture
def admin_client():
    """httpx.Client autenticado como admin."""
    with _login(BACKEND_URL, ADMIN_USERNAME, ADMIN_PASSWORD) as c:
        yield c


@pytest.fixture
def user_client():
    """httpx.Client autenticado como juanperez (CLIENTE)."""
    with _login(BACKEND_URL, USER_USERNAME, USER_PASSWORD) as c:
        yield c


@pytest.fixture
def new_user_client():
    """
    Registra un usuario nuevo con username único, devuelve client autenticado.
    El usuario generado no se puede eliminar vía API pública, pero es único
    gracias al uuid, por lo que no colisiona en ejecuciones posteriores.
    """
    suffix = uuid.uuid4().hex[:8]
    payload = {
        "username": f"test_{suffix}",
        "email": f"test_{suffix}@cumbre.test",
        "password": "Test1234!",
        "nombre": "Test",
        "apellido": "User",
    }
    resp = httpx.post(f"{BACKEND_URL}/auth/register", json=payload, timeout=10)
    resp.raise_for_status()
    token = resp.json()["token"]
    client = httpx.Client(
        base_url=BACKEND_URL,
        timeout=10,
        headers={"Authorization": f"Bearer {token}"},
    )
    client._auth_data = resp.json()  # type: ignore[attr-defined]
    with client:
        yield client


# ---------------------------------------------------------------------------
# Playwright fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def logged_in_page(page: Page):
    """Página con sesión iniciada como juanperez."""
    page.goto(f"{FRONTEND_URL}/login")
    page.get_by_label("Usuario").fill(USER_USERNAME)
    page.get_by_label("Contraseña").fill(USER_PASSWORD)
    page.get_by_role("button", name="Iniciar sesión").click()
    expect(page).to_have_url(f"{FRONTEND_URL}/", timeout=10_000)
    return page


@pytest.fixture
def admin_page(page: Page):
    """Página con sesión iniciada como admin."""
    page.goto(f"{FRONTEND_URL}/login")
    page.get_by_label("Usuario").fill(ADMIN_USERNAME)
    page.get_by_label("Contraseña").fill(ADMIN_PASSWORD)
    page.get_by_role("button", name="Iniciar sesión").click()
    expect(page).to_have_url(f"{FRONTEND_URL}/admin/dashboard", timeout=10_000)
    return page
