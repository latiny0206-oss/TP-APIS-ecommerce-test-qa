import os
import re

import pytest
from dotenv import load_dotenv
from playwright.sync_api import Page, expect

load_dotenv()
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")


@pytest.mark.e2e
def test_flujo_compra_completo_e2e(page: Page):
    """Flujo E2E completo: login → catálogo → agregar → carrito → checkout → confirmación."""

    # 1. Login como juanperez
    page.goto(f"{FRONTEND_URL}/login")
    page.get_by_label("Usuario").fill("juanperez")
    page.get_by_label("Contraseña").fill("user123")
    page.get_by_role("button", name="Iniciar sesión").click()
    expect(page).to_have_url(f"{FRONTEND_URL}/", timeout=10_000)

    # 2. Navegar al catálogo y hacer click en el primer producto
    page.goto(f"{FRONTEND_URL}/catalogo")
    page.wait_for_selector(".skeleton, [data-testid='skeleton']", state="hidden", timeout=15_000)
    page.locator("[data-testid='product-card'], .product-card, article").first.click()
    expect(page).to_have_url(re.compile(r"/producto/\d+"), timeout=10_000)

    # 3. Seleccionar talle disponible y agregar al carrito
    talle = page.locator(
        "button[data-talle]:not([disabled]):not(.sin-stock), "
        "[data-testid='size-button']:not([disabled])"
    ).first
    if talle.count() > 0:
        talle.click()

    page.get_by_role("button", name=re.compile("agregar al carrito", re.IGNORECASE)).click()
    expect(page.locator("text=/¡Agregado|Agregado al carrito/i")).to_be_visible(timeout=8_000)

    # 4. Ir al carrito y verificar que el item aparece
    page.goto(f"{FRONTEND_URL}/carrito")
    items_carrito = page.locator("[data-testid='cart-item'], .cart-item, .item-carrito")
    expect(items_carrito.first).to_be_visible(timeout=10_000)

    # 5. Aumentar cantidad con el botón +
    btn_mas = page.locator(
        "[data-testid='increase-quantity'], button[aria-label='Aumentar cantidad'], "
        "button:has-text('+')"
    ).first
    expect(btn_mas).to_be_visible(timeout=5_000)
    btn_mas.click()
    page.wait_for_timeout(800)

    # 6. Click "Ir al checkout"
    page.get_by_role("button", name=re.compile("ir al checkout|checkout|finalizar compra", re.IGNORECASE)).click()
    expect(page).to_have_url(re.compile(r"/checkout"), timeout=10_000)

    # 7. Llenar form de envío
    page.get_by_label(re.compile("nombre.*destinatario|nombre completo|nombre", re.IGNORECASE)).first.fill("Juan Perez")
    page.get_by_label(re.compile("dirección|direccion|calle", re.IGNORECASE)).first.fill("Av. Corrientes 1234")
    page.get_by_label(re.compile("ciudad", re.IGNORECASE)).first.fill("Buenos Aires")
    page.get_by_label(re.compile("provincia", re.IGNORECASE)).first.fill("Buenos Aires")
    page.get_by_label(re.compile("código postal|cp|zip", re.IGNORECASE)).first.fill("1043")
    page.get_by_label(re.compile("teléfono|telefono", re.IGNORECASE)).first.fill("1155550000")

    # 8. Ingresar cupón OTONO2026 y verificar "15% OFF"
    campo_cupon = page.get_by_label(re.compile("cupón|cupon|código de descuento", re.IGNORECASE)).or_(
        page.get_by_placeholder(re.compile("cupón|cupon|código", re.IGNORECASE))
    ).first
    if campo_cupon.count() > 0:
        campo_cupon.fill("OTONO2026")
        page.get_by_role("button", name=re.compile("aplicar cupón|aplicar|apply", re.IGNORECASE)).click()
        expect(page.locator("text=/15.*%.*OFF|15.*off|OTONO2026/i")).to_be_visible(timeout=8_000)

    # 9. Seleccionar método de pago
    metodo_pago = page.locator(
        "input[type='radio'][value='TRANSFERENCIA'], "
        "input[type='radio'][value='EFECTIVO'], "
        "label:has-text('Transferencia'), "
        "label:has-text('Efectivo')"
    ).first
    if metodo_pago.count() > 0:
        metodo_pago.click()

    # 10. Confirmar pedido
    page.get_by_role("button", name=re.compile("confirmar pedido|realizar pedido|pagar|confirmar", re.IGNORECASE)).click()

    # 11. Verificar redirección a /confirmacion con número de orden visible
    expect(page).to_have_url(re.compile(r"/confirmacion"), timeout=15_000)
    orden_numero = page.locator("text=/orden.*#?\\d+|#?\\d+.*orden|pedido.*#?\\d+/i, [data-testid='order-number']")
    expect(orden_numero.first).to_be_visible(timeout=10_000)
