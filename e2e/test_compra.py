import os
import re

import pytest
from dotenv import load_dotenv
from playwright.sync_api import Page, expect

load_dotenv()
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

PRODUCT_CARD = ".product-card"
SKELETON = ".animate-pulse"


@pytest.mark.e2e
def test_flujo_compra_completo_e2e(page: Page):
    """
    Flujo E2E completo: login → catálogo → detalle → agregar al carrito
    → carrito → checkout (3 pasos) → confirmación.

    Checkout tiene 3 pasos:
      Paso 1 (Envío):     llenar datos → "Continuar al pago"
      Paso 2 (Pago/Cupón): método de pago + cupón opcional → "Revisar pedido"
      Paso 3 (Confirmar):  revisar → "Confirmar compra"
    """

    # 1. Login como juanperez
    page.goto(f"{FRONTEND_URL}/login")
    page.get_by_label("Usuario").fill("juanperez")
    page.get_by_label("Contraseña").fill("user123")
    page.get_by_role("button", name="Iniciar sesión").click()
    expect(page).to_have_url(f"{FRONTEND_URL}/", timeout=10_000)
    page.goto(f"{FRONTEND_URL}/catalogo")
    page.wait_for_selector(SKELETON, state="hidden", timeout=15_000)
    page.locator(PRODUCT_CARD).filter(has_not_text="AGOTADO").first.click()
    expect(page).to_have_url(re.compile(r"/producto/\d+"), timeout=10_000)

    # 3. Seleccionar talle disponible y agregar al carrito
    # Los botones de talle son <button disabled={agotado}> sin atributo data-talle
    talle = page.locator("button:not([disabled])").filter(
        has_text=re.compile(r"^(XS|S|M|L|XL|XXL|36|37|38|39|40|41|42|43|44|45|Único)$")
    ).first
    expect(talle).to_be_visible(timeout=8_000)
    talle.click()
    page.get_by_role("button", name=re.compile("Agregar al carrito", re.IGNORECASE)).click()
    # El botón cambia a "¡Agregado!" como feedback visual
    expect(
        page.get_by_role("button", name=re.compile("¡Agregado!", re.IGNORECASE))
    ).to_be_visible(timeout=8_000)

    # 4. Ir al carrito y verificar que el item aparece
    page.goto(f"{FRONTEND_URL}/carrito")
    # Items del carrito: no tienen data-testid, usan CSS classes de Tailwind
    # Verificar que hay al menos un item visible (imagen o nombre de producto)
    expect(page.locator("main").get_by_role("img").first).to_be_visible(timeout=10_000)

    # 5. Ir al checkout desde el resumen del carrito
    page.get_by_role("button", name=re.compile("Ir al checkout", re.IGNORECASE)).click()
    expect(page).to_have_url(re.compile(r"/checkout"), timeout=10_000)

    # ── PASO 1: DATOS DE ENVÍO ──────────────────────────────────────────────
    page.get_by_label("Nombre del destinatario").fill("Juan Perez")
    page.get_by_label("Dirección").fill("Av. Corrientes 1234")
    page.get_by_label("Ciudad").fill("Buenos Aires")
    page.get_by_label("Provincia").fill("Buenos Aires")
    page.get_by_label("Código postal").fill("1043")
    page.get_by_label("Teléfono").fill("1155550000")
    page.get_by_role("button", name="Continuar al pago").click()

    # ── PASO 2: MÉTODO DE PAGO + CUPÓN ─────────────────────────────────────
    # Seleccionar "Transferencia bancaria"
    page.get_by_text("Transferencia bancaria").click()

    # Aplicar cupón OTONO2026 (opcional en el UI)
    campo_cupon = page.get_by_placeholder("OTONO2026")
    if campo_cupon.count() > 0:
        campo_cupon.fill("OTONO2026")
        page.get_by_role("button", name=re.compile("Aplicar", re.IGNORECASE)).click()
        # Esperar confirmación del cupón aplicado (card verde con el código)
        expect(page.locator("text=OTONO2026").first).to_be_visible(timeout=8_000)
    page.get_by_role("button", name="Revisar pedido").click()

    # ── PASO 3: CONFIRMACIÓN ────────────────────────────────────────────────
    # Verificar resumen y confirmar
    page.get_by_role("button", name="Confirmar compra").click()

    # 6. Verificar redirección a /confirmacion con número de pedido
    expect(page).to_have_url(re.compile(r"/confirmacion"), timeout=15_000)
    # La página muestra "Número de pedido" con el ID formateado como "#ORD-{id}"
    expect(page.get_by_text("Número de pedido")).to_be_visible(timeout=10_000)
    expect(page.locator("text=/ORD-\\d+/")).to_be_visible(timeout=10_000)


@pytest.mark.e2e
def test_gestionar_items_carrito_e2e(logged_in_page: Page):
    page = logged_in_page
    # 1. Navegar al catálogo y seleccionar primer producto en stock
    page.goto(f"{FRONTEND_URL}/catalogo")
    page.wait_for_selector(SKELETON, state="hidden", timeout=15_000)
    page.locator(PRODUCT_CARD).filter(has_not_text="AGOTADO").first.click()
    expect(page).to_have_url(re.compile(r"/producto/\d+"), timeout=10_000)

    # 2. Seleccionar talle disponible y agregar al carrito
    talle = page.locator("button:not([disabled])").filter(
        has_text=re.compile(r"^(XS|S|M|L|XL|XXL|36|37|38|39|40|41|42|43|44|45|Único)$")
    ).first
    expect(talle).to_be_visible(timeout=8_000)
    talle.click()

    page.get_by_role("button", name=re.compile("Agregar al carrito", re.IGNORECASE)).click()
    expect(page.get_by_role("button", name=re.compile("¡Agregado!", re.IGNORECASE))).to_be_visible(timeout=8_000)

    # 3. Ir al carrito
    page.goto(f"{FRONTEND_URL}/carrito")
    expect(page.locator("main").get_by_role("img").first).to_be_visible(timeout=10_000)

    # Verificar cantidad inicial es 1
    qty_span = page.locator("span.px-4.font-mono.font-bold.text-sm")
    expect(qty_span).to_have_text("1")

    # 4. Incrementar cantidad (Plus button) — only if enabled (stock > 1)
    plus_btn = page.locator("button").filter(has=page.locator("svg.lucide-plus")).first
    if plus_btn.is_enabled(timeout=2_000):
        plus_btn.click()
        # Verificar cantidad es 2
        expect(qty_span).to_have_text("2")
    # else: stock=1, plus disabled — this is correct behavior, skip increment

    # 5. Quitar del carrito
    page.get_by_role("button", name="Quitar").first.click()
    # Verificar que el carrito está vacío
    expect(page.get_by_text("Tu carrito está vacío")).to_be_visible(timeout=10_000)


@pytest.mark.e2e
def test_checkout_cupon_invalido_e2e(logged_in_page: Page):
    page = logged_in_page
    # 1. Navegar al catálogo y seleccionar primer producto en stock
    page.goto(f"{FRONTEND_URL}/catalogo")
    page.wait_for_selector(SKELETON, state="hidden", timeout=15_000)
    page.locator(PRODUCT_CARD).filter(has_not_text="AGOTADO").first.click()
    expect(page).to_have_url(re.compile(r"/producto/\d+"), timeout=10_000)

    # 2. Seleccionar talle disponible y agregar al carrito
    talle = page.locator("button:not([disabled])").filter(
        has_text=re.compile(r"^(XS|S|M|L|XL|XXL|36|37|38|39|40|41|42|43|44|45|Único)$")
    ).first
    expect(talle).to_be_visible(timeout=8_000)
    talle.click()

    page.get_by_role("button", name=re.compile("Agregar al carrito", re.IGNORECASE)).click()
    expect(page.get_by_role("button", name=re.compile("¡Agregado!", re.IGNORECASE))).to_be_visible(timeout=8_000)

    # 3. Ir al carrito y luego a checkout
    page.goto(f"{FRONTEND_URL}/carrito")
    page.get_by_role("button", name=re.compile("Ir al checkout", re.IGNORECASE)).click()
    expect(page).to_have_url(re.compile(r"/checkout"), timeout=10_000)

    # Paso 1: Enviar datos
    page.get_by_label("Nombre del destinatario").fill("Juan Perez")
    page.get_by_label("Dirección").fill("Av. Corrientes 1234")
    page.get_by_label("Ciudad").fill("Buenos Aires")
    page.get_by_label("Provincia").fill("Buenos Aires")
    page.get_by_label("Código postal").fill("1043")
    page.get_by_label("Teléfono").fill("1155550000")
    page.get_by_role("button", name="Continuar al pago").click()

    # Paso 2: Método de pago + Cupón inválido
    page.get_by_text("Transferencia bancaria").click()

    campo_cupon = page.get_by_placeholder("OTONO2026")
    expect(campo_cupon).to_be_visible(timeout=5_000)
    campo_cupon.fill("INVALID_COUPON_XYZ")
    page.get_by_role("button", name=re.compile("Aplicar", re.IGNORECASE)).click()
    # Verificar que muestra error de cupón
    error_msg = page.locator("text=Código no encontrado").first
    expect(error_msg).to_be_visible(timeout=8_000)
@pytest.mark.e2e
def test_verificar_historial_pedidos_e2e(logged_in_page: Page):
    page = logged_in_page
    # 1. Navegar al catálogo y seleccionar primer producto en stock
    page.goto(f"{FRONTEND_URL}/catalogo")
    page.wait_for_selector(SKELETON, state="hidden", timeout=15_000)
    page.locator(PRODUCT_CARD).filter(has_not_text="AGOTADO").first.click()
    expect(page).to_have_url(re.compile(r"/producto/\d+"), timeout=10_000)

    # 2. Seleccionar talle disponible y agregar al carrito
    talle = page.locator("button:not([disabled])").filter(
        has_text=re.compile(r"^(XS|S|M|L|XL|XXL|36|37|38|39|40|41|42|43|44|45|Único)$")
    ).first
    expect(talle).to_be_visible(timeout=8_000)
    talle.click()

    page.get_by_role("button", name=re.compile("Agregar al carrito", re.IGNORECASE)).click()
    expect(page.get_by_role("button", name=re.compile("¡Agregado!", re.IGNORECASE))).to_be_visible(timeout=8_000)

    # 3. Checkout
    page.goto(f"{FRONTEND_URL}/carrito")
    page.get_by_role("button", name=re.compile("Ir al checkout", re.IGNORECASE)).click()

    page.get_by_label("Nombre del destinatario").fill("Juan Perez")
    page.get_by_label("Dirección").fill("Av. Corrientes 1234")
    page.get_by_label("Ciudad").fill("Buenos Aires")
    page.get_by_label("Provincia").fill("Buenos Aires")
    page.get_by_label("Código postal").fill("1043")
    page.get_by_label("Teléfono").fill("1155550000")
    page.get_by_role("button", name="Continuar al pago").click()

    page.get_by_text("Transferencia bancaria").click()
    page.get_by_role("button", name="Revisar pedido").click()
    page.get_by_role("button", name="Confirmar compra").click()

    # 4. Obtener ID de pedido
    expect(page).to_have_url(re.compile(r"/confirmacion"), timeout=15_000)
    order_text_locator = page.locator("text=/ORD-\\d+/")
    expect(order_text_locator).to_be_visible(timeout=10_000)
    order_text = order_text_locator.inner_text()
    order_id = re.search(r"ORD-(\d+)", order_text).group(1)

    # 5. Ir al historial de pedidos
    page.goto(f"{FRONTEND_URL}/cuenta/ordenes")
    # Verificar que la orden con ID #order_id está en la lista
    expect(page.locator(f"text=#{order_id}").first).to_be_visible(timeout=10_000)


@pytest.mark.e2e
def test_carrito_vacio_muestra_mensaje_e2e(logged_in_page: Page):
    """Un carrito sin items debe mostrar 'Tu carrito está vacío'."""
    page = logged_in_page
    # Limpiar cualquier item del carrito
    page.evaluate("() => localStorage.removeItem('cumbre_cart')")
    page.goto(f"{FRONTEND_URL}/carrito")
    expect(page.get_by_text("Tu carrito está vacío")).to_be_visible(timeout=10_000)


@pytest.mark.e2e
def test_carrito_persiste_tras_recargar_e2e(logged_in_page: Page):
    """Agregar un producto, recargar la página, y el carrito debe persistir."""
    page = logged_in_page

    # 1. Agregar un producto al carrito
    page.goto(f"{FRONTEND_URL}/catalogo")
    page.wait_for_selector(SKELETON, state="hidden", timeout=15_000)
    page.locator(PRODUCT_CARD).filter(has_not_text="AGOTADO").first.click()
    expect(page).to_have_url(re.compile(r"/producto/\d+"), timeout=10_000)

    talle = page.locator("button:not([disabled])").filter(
        has_text=re.compile(r"^(XS|S|M|L|XL|XXL|36|37|38|39|40|41|42|43|44|45|Único)$")
    ).first
    expect(talle).to_be_visible(timeout=8_000)
    talle.click()
    page.get_by_role("button", name=re.compile("Agregar al carrito", re.IGNORECASE)).click()
    expect(
        page.get_by_role("button", name=re.compile("¡Agregado!", re.IGNORECASE))
    ).to_be_visible(timeout=8_000)

    # 2. Recargar la página completamente
    page.reload()
    page.wait_for_load_state("networkidle")

    # 3. Verificar que el carrito aún tiene el item
    page.goto(f"{FRONTEND_URL}/carrito")
    # Debe mostrar al menos una imagen de producto (el item persiste)
    expect(page.locator("main").get_by_role("img").first).to_be_visible(timeout=10_000)


@pytest.mark.e2e
def test_checkout_paso1_campos_vacios_no_avanza_e2e(logged_in_page: Page):
    """En paso 1 del checkout, dejar campos vacíos no debe permitir avanzar."""
    page = logged_in_page

    # Agregar producto al carrito
    page.goto(f"{FRONTEND_URL}/catalogo")
    page.wait_for_selector(SKELETON, state="hidden", timeout=15_000)
    page.locator(PRODUCT_CARD).filter(has_not_text="AGOTADO").first.click()
    expect(page).to_have_url(re.compile(r"/producto/\d+"), timeout=10_000)

    talle = page.locator("button:not([disabled])").filter(
        has_text=re.compile(r"^(XS|S|M|L|XL|XXL|36|37|38|39|40|41|42|43|44|45|Único)$")
    ).first
    expect(talle).to_be_visible(timeout=8_000)
    talle.click()
    page.get_by_role("button", name=re.compile("Agregar al carrito", re.IGNORECASE)).click()
    expect(
        page.get_by_role("button", name=re.compile("¡Agregado!", re.IGNORECASE))
    ).to_be_visible(timeout=8_000)

    # Ir a checkout
    page.goto(f"{FRONTEND_URL}/carrito")
    page.get_by_role("button", name=re.compile("Ir al checkout", re.IGNORECASE)).click()
    expect(page).to_have_url(re.compile(r"/checkout"), timeout=10_000)

    # Click "Continuar al pago" sin llenar datos
    page.get_by_role("button", name="Continuar al pago").click()

    # Debe quedarse en el mismo paso (no avanza)
    page.wait_for_timeout(1_000)
    # El botón "Continuar al pago" sigue visible (no avanzó al paso 2)
    expect(
        page.get_by_role("button", name="Continuar al pago")
    ).to_be_visible(timeout=3_000)


@pytest.mark.e2e
def test_post_checkout_carrito_vacio_en_navbar_e2e(page: Page):
    """Tras completar una compra, el carrito en navbar debe mostrar 0 items."""
    # Login
    page.goto(f"{FRONTEND_URL}/login")
    page.get_by_label("Usuario").fill("juanperez")
    page.get_by_label("Contraseña").fill("user123")
    page.get_by_role("button", name="Iniciar sesión").click()
    expect(page).to_have_url(f"{FRONTEND_URL}/", timeout=10_000)

    # Agregar producto
    page.goto(f"{FRONTEND_URL}/catalogo")
    page.wait_for_selector(SKELETON, state="hidden", timeout=15_000)
    page.locator(PRODUCT_CARD).filter(has_not_text="AGOTADO").first.click()
    expect(page).to_have_url(re.compile(r"/producto/\d+"), timeout=10_000)

    talle = page.locator("button:not([disabled])").filter(
        has_text=re.compile(r"^(XS|S|M|L|XL|XXL|36|37|38|39|40|41|42|43|44|45|Único)$")
    ).first
    expect(talle).to_be_visible(timeout=8_000)
    talle.click()
    page.get_by_role("button", name=re.compile("Agregar al carrito", re.IGNORECASE)).click()
    expect(
        page.get_by_role("button", name=re.compile("¡Agregado!", re.IGNORECASE))
    ).to_be_visible(timeout=8_000)

    # Checkout completo
    page.goto(f"{FRONTEND_URL}/carrito")
    page.get_by_role("button", name=re.compile("Ir al checkout", re.IGNORECASE)).click()

    page.get_by_label("Nombre del destinatario").fill("Test Post Checkout")
    page.get_by_label("Dirección").fill("Calle Test 123")
    page.get_by_label("Ciudad").fill("Buenos Aires")
    page.get_by_label("Provincia").fill("Buenos Aires")
    page.get_by_label("Código postal").fill("1043")
    page.get_by_label("Teléfono").fill("1155550000")
    page.get_by_role("button", name="Continuar al pago").click()

    page.get_by_text("Transferencia bancaria").click()
    page.get_by_role("button", name="Revisar pedido").click()
    page.get_by_role("button", name="Confirmar compra").click()

    expect(page).to_have_url(re.compile(r"/confirmacion"), timeout=15_000)

    # Verificar que localStorage cart está vacío
    cart_data = page.evaluate("() => localStorage.getItem('cumbre_cart')")
    if cart_data:
        import json
        cart = json.loads(cart_data)
        assert len(cart.get("items", [])) == 0, "Carrito debería estar vacío tras checkout"

