import os
import re
import uuid
from datetime import date, timedelta

import pytest
from dotenv import load_dotenv
from playwright.sync_api import Page, expect

load_dotenv()
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

# Ítems reales del sidebar según AdminLayout.jsx
# Orden: Tablero, Productos, Variantes, Catálogo, Descuentos, Órdenes, Usuarios, Mensajes
NAV_ITEMS = ["Tablero", "Productos", "Descuentos", "Órdenes", "Usuarios"]


@pytest.mark.e2e
class TestAdminLayout:
    def test_login_admin_muestra_sidebar_completo(self, admin_page: Page):
        page = admin_page
        sidebar = page.locator("aside, nav[aria-label='Administración'], [data-testid='sidebar']")
        expect(sidebar).to_be_visible(timeout=8_000)

        for item in NAV_ITEMS:
            expect(page.locator(f"text={item}").first).to_be_visible(timeout=5_000)


@pytest.mark.e2e
class TestAdminProductos:
    def test_tabla_productos_carga_y_boton_nuevo_visible(self, admin_page: Page):
        page = admin_page
        page.get_by_role("link", name=re.compile("Productos", re.IGNORECASE)).click()
        expect(page).to_have_url(re.compile(r"/admin/productos"), timeout=8_000)

        tabla = page.locator("table")
        expect(tabla).to_be_visible(timeout=10_000)

        # Hay dos botones "Nuevo producto" en el DOM (sidebar + main); scopear a main
        btn_nuevo = page.locator("main").get_by_role("button", name=re.compile("Nuevo producto", re.IGNORECASE))
        expect(btn_nuevo).to_be_visible(timeout=5_000)

    def test_crear_producto_via_drawer(self, admin_page: Page):
        page = admin_page
        page.goto(f"{FRONTEND_URL}/admin/productos")

        # Hay dos botones "Nuevo producto" en el DOM (sidebar + main); scopear a main
        btn_nuevo = page.locator("main").get_by_role("button", name=re.compile("Nuevo producto", re.IGNORECASE))
        expect(btn_nuevo).to_be_visible(timeout=10_000)
        btn_nuevo.click()

        # Drawer/modal se abre
        drawer = page.locator("[role='dialog'], .drawer, .modal")
        expect(drawer).to_be_visible(timeout=5_000)

        suffix = uuid.uuid4().hex[:6]
        nombre_producto = f"Prod E2E {suffix}"

        # Labels reales del formulario de producto
        page.get_by_label("Nombre").fill(nombre_producto)
        page.get_by_label(re.compile("Precio base", re.IGNORECASE)).fill("12000")
        desc_field = page.get_by_label(re.compile("Descripción", re.IGNORECASE))
        if desc_field.count() > 0:
            desc_field.fill("Producto creado por E2E test")

        # Select de categoría (dinámico)
        cat_select = page.locator("select[name='categoriaId']").or_(
            page.get_by_label(re.compile("Categoría", re.IGNORECASE))
        ).first
        if cat_select.count() > 0:
            cat_select.select_option(index=1)

        # Select de marca (dinámico)
        marca_select = page.locator("select[name='marcaId']").or_(
            page.get_by_label(re.compile("Marca", re.IGNORECASE))
        ).first
        if marca_select.count() > 0:
            marca_select.select_option(index=1)

        # Guardar
        page.get_by_role("button", name=re.compile("Guardar", re.IGNORECASE)).click()

        expect(drawer).to_be_hidden(timeout=8_000)
        expect(page.locator(f"text={nombre_producto}")).to_be_visible(timeout=10_000)


@pytest.mark.e2e
class TestAdminDescuentos:
    def test_lista_descuentos_carga(self, admin_page: Page):
        page = admin_page
        # Ruta real: /admin/descuentos (no /admin/cupones)
        page.get_by_role("link", name=re.compile("Descuentos", re.IGNORECASE)).click()
        expect(page).to_have_url(re.compile(r"/admin/descuentos"), timeout=8_000)

        # El panel muestra cards, no tabla
        expect(page.locator("text=OTONO2026")).to_be_visible(timeout=10_000)

    def test_crear_descuento_aparece_en_lista(self, admin_page: Page):
        page = admin_page
        page.goto(f"{FRONTEND_URL}/admin/descuentos")
        expect(page).to_have_url(re.compile(r"/admin/descuentos"), timeout=8_000)

        # El botón tiene texto exacto "Nuevo cupón" (con tilde)
        btn_nuevo = page.get_by_role("button", name="Nuevo cupón")
        expect(btn_nuevo).to_be_visible(timeout=10_000)
        btn_nuevo.click()

        drawer = page.locator("[role='dialog'], .drawer, .modal")
        expect(drawer).to_be_visible(timeout=5_000)

        suffix = uuid.uuid4().hex[:4].upper()
        codigo = f"E2E{suffix}"
        hoy = date.today()

        page.get_by_label(re.compile("Código", re.IGNORECASE)).fill(codigo)

        # Tipo
        tipo_select = page.locator("select[name='tipo']").or_(
            page.get_by_label(re.compile("Tipo", re.IGNORECASE))
        ).first
        if tipo_select.count() > 0:
            tipo_select.select_option("PORCENTAJE")

        # Valor/Porcentaje
        valor_field = page.get_by_label(re.compile("Porcentaje|Valor", re.IGNORECASE)).first
        if valor_field.count() > 0:
            valor_field.fill("20")

        # Fechas
        fecha_inicio = page.get_by_label(re.compile("Fecha.*inicio|inicio", re.IGNORECASE)).first
        fecha_fin = page.get_by_label(re.compile("Fecha.*fin|vencimiento", re.IGNORECASE)).first
        if fecha_inicio.count() > 0:
            fecha_inicio.fill(hoy.isoformat())
        if fecha_fin.count() > 0:
            fecha_fin.fill((hoy + timedelta(days=30)).isoformat())

        page.get_by_role("button", name=re.compile("Guardar|Crear|Aceptar", re.IGNORECASE)).click()
        expect(drawer).to_be_hidden(timeout=8_000)
        expect(page.locator(f"text={codigo}")).to_be_visible(timeout=10_000)

    def test_toggle_descuento(self, admin_page: Page):
        page = admin_page
        page.goto(f"{FRONTEND_URL}/admin/descuentos")
        expect(page).to_have_url(re.compile(r"/admin/descuentos"), timeout=8_000)

        # Toggle switch en las cards de descuento
        toggle = page.locator("input[type='checkbox'][role='switch']").first
        if toggle.count() > 0:
            estado_inicial = toggle.is_checked()
            toggle.click()
            page.wait_for_timeout(1_000)
            assert toggle.is_checked() != estado_inicial, "El toggle no cambió de estado"


@pytest.mark.e2e
class TestAdminOrdenes:
    def test_lista_ordenes_carga(self, admin_page: Page):
        page = admin_page
        # Ruta real: /admin/ordenes
        page.get_by_role("link", name=re.compile("Órdenes|Ordenes", re.IGNORECASE)).click()
        expect(page).to_have_url(re.compile(r"/admin/ordenes"), timeout=8_000)

        tabla = page.locator("table")
        expect(tabla).to_be_visible(timeout=10_000)


@pytest.mark.e2e
class TestAdminUsuarios:
    def test_lista_usuarios_carga(self, admin_page: Page):
        page = admin_page
        # Ruta real: /admin/usuarios
        page.get_by_role("link", name=re.compile("Usuarios|Clientes", re.IGNORECASE)).click()
        expect(page).to_have_url(re.compile(r"/admin/usuarios"), timeout=8_000)

        tabla = page.locator("table")
        expect(tabla).to_be_visible(timeout=10_000)


@pytest.mark.e2e
class TestAdminDashboard:
    def test_dashboard_muestra_kpis(self, admin_page: Page):
        page = admin_page
        # Ir al dashboard via sidebar ("Tablero", no "Dashboard")
        page.get_by_role("link", name=re.compile("Tablero", re.IGNORECASE)).click()
        expect(page).to_have_url(re.compile(r"/admin/dashboard"), timeout=8_000)

        # Los 4 KPIs reales del dashboard (labels exactos del componente)
        kpi_labels = [
            "Productos activos",
            "Órdenes pendientes",
            "Descuentos activos",
            "Clientes registrados",
        ]
        for label in kpi_labels:
            expect(page.get_by_text(label)).to_be_visible(timeout=10_000)
