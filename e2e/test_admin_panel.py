
import os
import re
import uuid
from datetime import date, timedelta

import pytest
from dotenv import load_dotenv
from playwright.sync_api import Page, expect

load_dotenv()
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

NAV_ITEMS = ["Dashboard", "Productos", "Órdenes", "Cupones", "Usuarios"]


@pytest.mark.e2e
class TestAdminLayout:
    def test_login_admin_muestra_sidebar_completo(self, admin_page: Page):
        page = admin_page
        sidebar = page.locator("nav[aria-label='Administración'], aside, [data-testid='sidebar']")
        expect(sidebar).to_be_visible(timeout=8_000)

        for item in NAV_ITEMS:
            expect(
                page.locator(f"text={item}").first
            ).to_be_visible(timeout=5_000)


@pytest.mark.e2e
class TestAdminProductos:
    def test_tabla_productos_carga_y_boton_nuevo_visible(self, admin_page: Page):
        page = admin_page
        page.get_by_role("link", name=re.compile("Productos", re.IGNORECASE)).click()
        expect(page).to_have_url(re.compile(r"/admin/productos"), timeout=8_000)

        tabla = page.locator("table, [data-testid='products-table'], .products-table")
        expect(tabla).to_be_visible(timeout=10_000)

        btn_nuevo = page.get_by_role("button", name=re.compile("nuevo producto|agregar producto", re.IGNORECASE))
        expect(btn_nuevo).to_be_visible(timeout=5_000)

    def test_crear_producto_via_drawer(self, admin_page: Page):
        page = admin_page
        page.goto(f"{FRONTEND_URL}/admin/productos")

        btn_nuevo = page.get_by_role("button", name=re.compile("nuevo producto|agregar producto", re.IGNORECASE))
        expect(btn_nuevo).to_be_visible(timeout=10_000)
        btn_nuevo.click()

        # Esperar que se abra el drawer/modal
        drawer = page.locator("[role='dialog'], .drawer, .modal, [data-testid='product-drawer']")
        expect(drawer).to_be_visible(timeout=5_000)

        suffix = uuid.uuid4().hex[:6]
        nombre_producto = f"Prod E2E {suffix}"

        page.get_by_label(re.compile("nombre", re.IGNORECASE)).fill(nombre_producto)
        page.get_by_label(re.compile("precio|precioBase", re.IGNORECASE)).fill("12000")
        page.get_by_label(re.compile("descripción|descripcion", re.IGNORECASE)).fill("Producto creado por E2E test")

        # Seleccionar categoría
        cat_select = page.locator("select[name='categoriaId'], [data-testid='categoria-select']").or_(
            page.get_by_label(re.compile("categoría|categoria", re.IGNORECASE))
        ).first
        cat_select.select_option(index=1)

        # Seleccionar marca
        marca_select = page.locator("select[name='marcaId'], [data-testid='marca-select']").or_(
            page.get_by_label(re.compile("marca", re.IGNORECASE))
        ).first
        marca_select.select_option(index=1)

        # Guardar
        page.get_by_role("button", name=re.compile("guardar|crear|aceptar", re.IGNORECASE)).click()

        # El drawer debe cerrarse
        expect(drawer).to_be_hidden(timeout=8_000)

        # El producto debe aparecer en la lista
        expect(page.locator(f"text={nombre_producto}")).to_be_visible(timeout=10_000)


@pytest.mark.e2e
class TestAdminCupones:
    def test_lista_cupones_carga(self, admin_page: Page):
        page = admin_page
        page.get_by_role("link", name=re.compile("Cupones|Descuentos", re.IGNORECASE)).click()
        expect(page).to_have_url(re.compile(r"/admin/(cupones|descuentos)"), timeout=8_000)

        tabla = page.locator("table, [data-testid='discounts-table'], .discounts-table")
        expect(tabla).to_be_visible(timeout=10_000)

    def test_crear_cupon_aparece_en_lista(self, admin_page: Page):
        page = admin_page
        page.goto(f"{FRONTEND_URL}/admin/cupones")
        page.wait_for_url(re.compile(r"/admin/(cupones|descuentos)"), timeout=8_000)

        btn_nuevo = page.get_by_role("button", name=re.compile("nuevo cupón|nuevo descuento|agregar", re.IGNORECASE))
        expect(btn_nuevo).to_be_visible(timeout=10_000)
        btn_nuevo.click()

        drawer = page.locator("[role='dialog'], .drawer, .modal")
        expect(drawer).to_be_visible(timeout=5_000)

        suffix = uuid.uuid4().hex[:4].upper()
        codigo = f"E2E{suffix}"
        hoy = date.today()

        page.get_by_label(re.compile("código|codigo", re.IGNORECASE)).fill(codigo)
        page.get_by_label(re.compile("nombre", re.IGNORECASE)).fill(f"Cupón E2E {suffix}")
        page.get_by_label(re.compile("valor|descuento", re.IGNORECASE)).fill("20")

        # Tipo PORCENTAJE
        tipo_select = page.locator("select[name='tipo']").or_(
            page.get_by_label(re.compile("tipo", re.IGNORECASE))
        ).first
        if tipo_select.count() > 0:
            tipo_select.select_option("PORCENTAJE")

        # Fechas
        fecha_inicio = page.get_by_label(re.compile("fecha.*inicio|inicio", re.IGNORECASE)).first
        fecha_fin = page.get_by_label(re.compile("fecha.*fin|vencimiento", re.IGNORECASE)).first
        if fecha_inicio.count() > 0:
            fecha_inicio.fill(hoy.isoformat())
        if fecha_fin.count() > 0:
            fecha_fin.fill((hoy + timedelta(days=30)).isoformat())

        page.get_by_role("button", name=re.compile("guardar|crear|aceptar", re.IGNORECASE)).click()
        expect(drawer).to_be_hidden(timeout=8_000)
        expect(page.locator(f"text={codigo}")).to_be_visible(timeout=10_000)

    def test_toggle_cupon(self, admin_page: Page):
        page = admin_page
        page.goto(f"{FRONTEND_URL}/admin/cupones")
        page.wait_for_url(re.compile(r"/admin/(cupones|descuentos)"), timeout=8_000)

        toggle = page.locator("input[type='checkbox'][role='switch'], [data-testid='discount-toggle']").first
        if toggle.count() > 0:
            estado_inicial = toggle.is_checked()
            toggle.click()
            page.wait_for_timeout(1_000)
            assert toggle.is_checked() != estado_inicial, "El toggle no cambió de estado"


@pytest.mark.e2e
class TestAdminOrdenes:
    def test_lista_ordenes_carga(self, admin_page: Page):
        page = admin_page
        page.get_by_role("link", name=re.compile("Órdenes|Ordenes|Pedidos", re.IGNORECASE)).click()
        expect(page).to_have_url(re.compile(r"/admin/ordenes"), timeout=8_000)

        tabla = page.locator("table, [data-testid='orders-table']")
        expect(tabla).to_be_visible(timeout=10_000)


@pytest.mark.e2e
class TestAdminUsuarios:
    def test_lista_usuarios_carga(self, admin_page: Page):
        page = admin_page
        page.get_by_role("link", name=re.compile("Usuarios|Clientes", re.IGNORECASE)).click()
        expect(page).to_have_url(re.compile(r"/admin/usuarios"), timeout=8_000)

        tabla = page.locator("table, [data-testid='users-table']")
        expect(tabla).to_be_visible(timeout=10_000)


@pytest.mark.e2e
class TestAdminDashboard:
    def test_dashboard_muestra_kpis(self, admin_page: Page):
        page = admin_page
        page.get_by_role("link", name=re.compile("Dashboard|Inicio", re.IGNORECASE)).click()
        expect(page).to_have_url(re.compile(r"/admin/dashboard"), timeout=8_000)

        # KPIs deben ser visibles con números
        kpi_locator = page.locator(
            "[data-testid='kpi'], .kpi, .stat-card, .dashboard-card, .metric"
        )
        expect(kpi_locator.first).to_be_visible(timeout=10_000)

        # Debe haber al menos 4 KPIs (productos, órdenes, descuentos, clientes)
        count = kpi_locator.count()
        assert count >= 4, f"Se esperaban al menos 4 KPIs, encontrados {count}"
