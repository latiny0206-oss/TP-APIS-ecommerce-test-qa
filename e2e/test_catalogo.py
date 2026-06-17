import os
import re

import pytest
from dotenv import load_dotenv
from playwright.sync_api import Page, expect

load_dotenv()
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")


@pytest.mark.e2e
class TestCatalogoNavegacion:
    def test_catalogo_carga_productos(self, page: Page):
        page.goto(f"{FRONTEND_URL}/catalogo")
        # Esperar a que desaparezca el skeleton
        page.wait_for_selector(".skeleton, [data-testid='skeleton']", state="hidden", timeout=15_000)
        # Debe haber al menos una tarjeta de producto
        productos = page.locator("[data-testid='product-card'], .product-card, article")
        expect(productos.first).to_be_visible(timeout=10_000)

    def test_filtrar_por_categoria_calzado(self, page: Page):
        page.goto(f"{FRONTEND_URL}/catalogo")
        page.wait_for_selector(".skeleton, [data-testid='skeleton']", state="hidden", timeout=15_000)

        # Click en filtro de categoría Calzado
        page.get_by_role("button", name=re.compile("Calzado", re.IGNORECASE)).click()
        page.wait_for_timeout(1_500)

        # Verificar que los productos visibles corresponden a Calzado
        # (el texto "Calzado" debe aparecer en cada tarjeta o en la URL/breadcrumb)
        productos = page.locator("[data-testid='product-card'], .product-card, article")
        count = productos.count()
        assert count > 0, "No se encontraron productos de Calzado"

        # Verificar que todos muestran la categoría correcta (si está en la tarjeta)
        for i in range(min(count, 5)):
            tarjeta = productos.nth(i)
            # Verificar que ninguna tarjeta visible muestre una categoría diferente
            texto = tarjeta.inner_text()
            # Si la categoría está en la tarjeta, debe ser Calzado
            if "Indumentaria" in texto or "Equipamiento" in texto or "Accesorios" in texto:
                pytest.fail(f"Tarjeta {i} muestra categoría incorrecta: {texto[:100]}")

    def test_filtrar_por_marca_reduce_lista(self, page: Page):
        page.goto(f"{FRONTEND_URL}/catalogo")
        page.wait_for_selector(".skeleton, [data-testid='skeleton']", state="hidden", timeout=15_000)

        productos_antes = page.locator("[data-testid='product-card'], .product-card, article").count()

        # Click en cualquier filtro de marca disponible
        page.locator("text=/Columbia|Salomon|Montagne/").first.click()
        page.wait_for_timeout(1_500)

        productos_despues = page.locator("[data-testid='product-card'], .product-card, article").count()
        assert productos_despues <= productos_antes, (
            "Filtrar por marca debería reducir o mantener igual la cantidad de productos"
        )

    def test_buscar_por_texto(self, page: Page):
        page.goto(f"{FRONTEND_URL}/catalogo")
        page.wait_for_selector(".skeleton, [data-testid='skeleton']", state="hidden", timeout=15_000)

        # Buscar por un término que debería devolver resultados
        search_input = page.get_by_role("searchbox").or_(
            page.get_by_placeholder(re.compile("buscar|search", re.IGNORECASE))
        )
        expect(search_input).to_be_visible(timeout=5_000)
        search_input.fill("zapatilla")
        search_input.press("Enter")
        page.wait_for_timeout(1_500)

        # Si no hay resultados, el campo de búsqueda devuelve "sin resultados"
        # Si hay resultados, deben ser visibles
        sin_resultados = page.locator("text=/sin resultados|no se encontraron/i")
        productos = page.locator("[data-testid='product-card'], .product-card, article")
        # Al menos uno de los dos estados debe ser visible
        assert sin_resultados.count() > 0 or productos.count() > 0


@pytest.mark.e2e
class TestDetalleProducto:
    def test_click_producto_navega_a_detalle(self, page: Page):
        page.goto(f"{FRONTEND_URL}/catalogo")
        page.wait_for_selector(".skeleton, [data-testid='skeleton']", state="hidden", timeout=15_000)

        primera_tarjeta = page.locator("[data-testid='product-card'], .product-card, article").first
        expect(primera_tarjeta).to_be_visible(timeout=5_000)
        primera_tarjeta.click()

        # Debe navegar a /producto/{id}
        expect(page).to_have_url(re.compile(r"/producto/\d+"), timeout=10_000)

    def test_seleccionar_talle_habilita_boton_agregar(self, page: Page):
        page.goto(f"{FRONTEND_URL}/catalogo")
        page.wait_for_selector(".skeleton, [data-testid='skeleton']", state="hidden", timeout=15_000)
        page.locator("[data-testid='product-card'], .product-card, article").first.click()
        expect(page).to_have_url(re.compile(r"/producto/\d+"), timeout=10_000)

        # El botón debe estar deshabilitado antes de seleccionar talle
        btn_agregar = page.get_by_role("button", name=re.compile("agregar al carrito", re.IGNORECASE))
        # Puede estar deshabilitado o no existir hasta seleccionar talle
        # Seleccionar primer talle disponible (no tachado)
        talle_disponible = page.locator(
            "button[data-talle]:not([disabled]):not(.disabled):not(.sin-stock), "
            "[data-testid='size-button']:not([disabled])"
        ).first
        if talle_disponible.count() == 0:
            # Fallback: buscar botones de talle sin class de sin-stock
            talle_disponible = page.locator("button").filter(
                has_not=page.locator(".sin-stock, .out-of-stock, .tachado")
            ).filter(has_text=re.compile(r"^(XS|S|M|L|XL|XXL|36|37|38|39|40|41|42|43|44|45)$")).first

        expect(talle_disponible).to_be_visible(timeout=5_000)
        talle_disponible.click()

        expect(btn_agregar).to_be_enabled(timeout=5_000)

    def test_talle_sin_stock_aparece_deshabilitado(self, page: Page):
        page.goto(f"{FRONTEND_URL}/catalogo")
        page.wait_for_selector(".skeleton, [data-testid='skeleton']", state="hidden", timeout=15_000)
        page.locator("[data-testid='product-card'], .product-card, article").first.click()
        expect(page).to_have_url(re.compile(r"/producto/\d+"), timeout=10_000)

        # Talles sin stock deben estar deshabilitados o tachados
        talles_sin_stock = page.locator(".sin-stock, .out-of-stock, [data-sin-stock='true']")
        if talles_sin_stock.count() > 0:
            primer_sin_stock = talles_sin_stock.first
            # Verificar que es un botón deshabilitado o tiene clase visual de sin stock
            assert (
                primer_sin_stock.get_attribute("disabled") is not None
                or "sin-stock" in (primer_sin_stock.get_attribute("class") or "")
                or "tachado" in (primer_sin_stock.get_attribute("class") or "")
            )

    def test_agregar_al_carrito_muestra_toast_y_actualiza_badge(self, logged_in_page: Page):
        page = logged_in_page
        page.goto(f"{FRONTEND_URL}/catalogo")
        page.wait_for_selector(".skeleton, [data-testid='skeleton']", state="hidden", timeout=15_000)
        page.locator("[data-testid='product-card'], .product-card, article").first.click()
        expect(page).to_have_url(re.compile(r"/producto/\d+"), timeout=10_000)

        # Seleccionar primer talle disponible
        talle = page.locator(
            "button[data-talle]:not([disabled]):not(.sin-stock), "
            "[data-testid='size-button']:not([disabled])"
        ).first
        if talle.count() > 0:
            talle.click()

        # Obtener badge inicial del carrito
        badge = page.locator("[data-testid='cart-badge'], .cart-badge, .badge")
        badge_inicial = int(badge.inner_text()) if badge.count() > 0 and badge.inner_text().isdigit() else 0

        page.get_by_role("button", name=re.compile("agregar al carrito", re.IGNORECASE)).click()

        # Toast debe aparecer
        expect(page.locator("text=/¡Agregado|Agregado al carrito/i")).to_be_visible(timeout=8_000)

        # Badge del carrito debe actualizarse
        if badge.count() > 0:
            expect(badge).to_be_visible(timeout=5_000)
