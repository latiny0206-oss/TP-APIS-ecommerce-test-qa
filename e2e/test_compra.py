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

    # 2. Ir al catálogo y hacer click en el primer producto
    page.goto(f"{FRONTEND_URL}/catalogo")
    page.wait_for_selector(SKELETON, state="hidden", timeout=15_000)
    page.locator(PRODUCT_CARD).first.click()
    expect(page).to_have_url(re.compile(r"/producto/\d+"), timeout=10_000)

    # 3. Seleccionar talle disponible y agregar al carrito
    # Los botones de talle son <button disabled={agotado}> sin atributo data-talle
    talle = page.locator("button:not([disabled])").filter(
        has_text=re.compile(r"^(XS|S|M|L|XL|XXL|36|37|38|39|40|41|42|43|44|45|Único)$")
    ).first
    if talle.count() > 0:
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
        expect(page.locator("text=OTONO2026")).to_be_visible(timeout=8_000)

    page.get_by_role("button", name="Revisar pedido").click()

    # ── PASO 3: CONFIRMACIÓN ────────────────────────────────────────────────
    # Verificar resumen y confirmar
    page.get_by_role("button", name="Confirmar compra").click()

    # 6. Verificar redirección a /confirmacion con número de pedido
    expect(page).to_have_url(re.compile(r"/confirmacion"), timeout=15_000)
    # La página muestra "Número de pedido" con el ID formateado como "#ORD-{id}"
    expect(page.get_by_text("Número de pedido")).to_be_visible(timeout=10_000)
    expect(page.locator("text=/ORD-\\d+/")).to_be_visible(timeout=10_000)
