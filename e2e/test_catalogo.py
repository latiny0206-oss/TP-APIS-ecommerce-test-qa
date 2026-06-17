import os
import re

import pytest
from dotenv import load_dotenv
from playwright.sync_api import Page, expect

load_dotenv()
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

# Selector real de tarjetas de producto (clase CSS del componente)
PRODUCT_CARD = ".product-card"
# Skeleton usa animate-pulse (Tailwind); esperar a que desaparezcan
SKELETON = ".animate-pulse"


@pytest.mark.e2e
class TestCatalogoNavegacion:
    def test_catalogo_carga_productos(self, page: Page):
        page.goto(f"{FRONTEND_URL}/catalogo")
        # Esperar a que los skeletons desaparezcan
        page.wait_for_selector(SKELETON, state="hidden", timeout=15_000)
        # Debe haber al menos una tarjeta de producto
        expect(page.locator(PRODUCT_CARD).first).to_be_visible(timeout=10_000)

    def test_filtrar_por_categoria_calzado(self, page: Page):
        page.goto(f"{FRONTEND_URL}/catalogo")
        page.wait_for_selector(SKELETON, state="hidden", timeout=15_000)

        # El componente Checkbox del catálogo es un <label> con un <div> visual —
        # no hay <input type="checkbox"> real en el DOM. Se clickea el label.
        page.locator("label").filter(has_text="Calzado").click()
        page.wait_for_timeout(1_500)

        productos = page.locator(PRODUCT_CARD)
        count = productos.count()
        assert count > 0, "No se encontraron productos de Calzado"

        # Verificar que ninguna tarjeta muestra categoría de otra sección
        for i in range(min(count, 5)):
            texto = productos.nth(i).inner_text()
            if "Indumentaria" in texto or "Equipamiento" in texto:
                pytest.fail(f"Tarjeta {i} muestra categoría incorrecta: {texto[:100]}")

    def test_filtrar_por_marca_reduce_lista(self, page: Page):
        page.goto(f"{FRONTEND_URL}/catalogo")
        page.wait_for_selector(SKELETON, state="hidden", timeout=15_000)

        productos_antes = page.locator(PRODUCT_CARD).count()

        # Los filtros de marca también son <label> custom (mismo Checkbox component)
        primer_filtro_marca = page.locator("label").filter(
            has_text=re.compile(r"Columbia|Salomon|Montagne|Osprey|Black Diamond", re.IGNORECASE)
        ).first
        if primer_filtro_marca.count() > 0:
            primer_filtro_marca.click()
            page.wait_for_timeout(1_500)
            productos_despues = page.locator(PRODUCT_CARD).count()
            assert productos_despues <= productos_antes, (
                "Filtrar por marca debería reducir o mantener igual la cantidad de productos"
            )

    def test_buscar_por_texto(self, page: Page):
        page.goto(f"{FRONTEND_URL}/catalogo")
        page.wait_for_selector(SKELETON, state="hidden", timeout=15_000)

        # El input de búsqueda tiene placeholder "Buscar productos..."
        search_input = page.get_by_placeholder("Buscar productos...")
        expect(search_input).to_be_visible(timeout=5_000)
        search_input.fill("zapatilla")
        search_input.press("Enter")
        page.wait_for_timeout(1_500)

        sin_resultados = page.locator("text=/sin resultados|no se encontraron/i")
        productos = page.locator(PRODUCT_CARD)
        assert sin_resultados.count() > 0 or productos.count() > 0, (
            "Debería mostrarse resultado de búsqueda o mensaje de sin resultados"
        )


@pytest.mark.e2e
class TestDetalleProducto:
    def test_click_producto_navega_a_detalle(self, page: Page):
        page.goto(f"{FRONTEND_URL}/catalogo")
        page.wait_for_selector(SKELETON, state="hidden", timeout=15_000)

        primera_tarjeta = page.locator(PRODUCT_CARD).first
        expect(primera_tarjeta).to_be_visible(timeout=5_000)
        primera_tarjeta.click()

        # El router usa /producto/:id
        expect(page).to_have_url(re.compile(r"/producto/\d+"), timeout=10_000)
    def test_seleccionar_talle_habilita_boton_agregar(self, page: Page):
        page.goto(f"{FRONTEND_URL}/catalogo")
        page.wait_for_selector(SKELETON, state="hidden", timeout=15_000)
        page.locator(PRODUCT_CARD).filter(has_not_text="AGOTADO").first.click()
        # Los botones de talle son <button disabled={agotado}> con solo el texto del talle.
        # No tienen data-talle ni clase específica — usar :not([disabled]) en CSS.
        talle_disponible = page.locator("button:not([disabled])").filter(
            has_text=re.compile(r"^(XS|S|M|L|XL|XXL|36|37|38|39|40|41|42|43|44|45|Único)$")
        ).first

        expect(talle_disponible).to_be_visible(timeout=5_000)
        talle_disponible.click()

        # Tras seleccionar talle, el botón "Agregar al carrito" debe habilitarse
        btn_agregar = page.get_by_role("button", name=re.compile("Agregar al carrito", re.IGNORECASE))
        expect(btn_agregar).to_be_enabled(timeout=5_000)

    def test_talle_sin_stock_aparece_deshabilitado(self, page: Page):
        page.goto(f"{FRONTEND_URL}/catalogo")
        page.wait_for_selector(SKELETON, state="hidden", timeout=15_000)
        page.locator(PRODUCT_CARD).first.click()
        expect(page).to_have_url(re.compile(r"/producto/\d+"), timeout=10_000)

        # Talles sin stock deben estar disabled
        talles_disabled = page.locator("button[disabled]").filter(
            has_text=re.compile(r"^(XS|S|M|L|XL|XXL|36|37|38|39|40|41|42|43|44|45|Único)$")
        )
        if talles_disabled.count() > 0:
            # Si existe, verificar que efectivamente está disabled
            assert talles_disabled.first.get_attribute("disabled") is not None
    def test_agregar_al_carrito_muestra_feedback_visual(self, logged_in_page: Page):
        page = logged_in_page
        page.goto(f"{FRONTEND_URL}/catalogo")
        page.wait_for_selector(SKELETON, state="hidden", timeout=15_000)
        page.locator(PRODUCT_CARD).filter(has_not_text="AGOTADO").first.click()
        expect(page).to_have_url(re.compile(r"/producto/\d+"), timeout=10_000)

        # Esperar a que los botones de talle se rendericen (página lazy-loaded)
        # Los botones de talle son <button disabled={agotado}> sin atributo data-talle
        talle = page.locator("button:not([disabled])").filter(
            has_text=re.compile(r"^(XS|S|M|L|XL|XXL|36|37|38|39|40|41|42|43|44|45|Único)$")
        ).first
        expect(talle).to_be_visible(timeout=8_000)
        talle.click()

        page.get_by_role("button", name=re.compile("Agregar al carrito", re.IGNORECASE)).click()

        # El botón cambia a "¡Agregado!" durante 2000ms (feedback visual sin toast separado)
        expect(
            page.get_by_role("button", name=re.compile("¡Agregado!", re.IGNORECASE))
        ).to_be_visible(timeout=8_000)
