"""
Flujo completo de compra:
registro → login → buscar variante con stock → crear carrito (estado inicial VACIO)
→ agregar item (carrito pasa a ACTIVO) → aplicar cupón → checkout
→ verificar orden PENDIENTE, monto con descuento, stock decrementado, carrito CONVERTIDO.

Estados del carrito (EstadoCarrito enum):
  VACIO      → carrito recién creado, sin items
  ACTIVO     → carrito con al menos un item
  ABANDONADO → carrito no completado
  CONVERTIDO → checkout realizado
"""

import uuid

import httpx
import pytest


def _backend_url():
    import os
    from dotenv import load_dotenv
    load_dotenv()
    return os.getenv("BACKEND_URL", "http://localhost:8080/api")


@pytest.mark.integration
def test_flujo_compra_completo():
    base = _backend_url()

    # 1. Registrar usuario nuevo
    suffix = uuid.uuid4().hex[:10]
    reg_payload = {
        "username": f"comprador_{suffix}",
        "email": f"comprador_{suffix}@cumbre.test",
        "password": "Compra1234!",
        "nombre": "Comprador",
        "apellido": "Test",
    }
    reg_resp = httpx.post(f"{base}/auth/register", json=reg_payload, timeout=10)
    assert reg_resp.status_code == 201, f"Registro falló: {reg_resp.text}"
    user_id = reg_resp.json()["id"]

    # 2. Login (obtener token fresco)
    login_resp = httpx.post(f"{base}/auth/login", json={
        "username": reg_payload["username"],
        "password": reg_payload["password"],
    }, timeout=10)
    assert login_resp.status_code == 200
    token = login_resp.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Obtener variante con stock disponible
    all_variantes = httpx.get(f"{base}/variantes", timeout=10).json()
    variante_elegida = next((v for v in all_variantes if v.get("stock", 0) > 0), None)
    assert variante_elegida is not None, "No hay variantes con stock"
    stock_inicial = variante_elegida["stock"]

    # 4. Crear carrito — estado inicial es VACIO (sin items)
    carrito_resp = httpx.post(f"{base}/carritos", json={"usuarioId": user_id}, headers=headers, timeout=10)
    assert carrito_resp.status_code in (200, 201)
    carrito = carrito_resp.json()
    assert carrito["estado"] == "VACIO", (
        f"Estado esperado VACIO para carrito nuevo, obtenido: {carrito['estado']}"
    )
    carrito_id = carrito["id"]

    # 5. Agregar variante al carrito
    # POST /carritos/{id}/items devuelve ItemCarritoResponse (no CarritoResponse)
    add_resp = httpx.post(
        f"{base}/carritos/{carrito_id}/items",
        json={"idVariante": variante_elegida["id"], "cantidad": 1},
        headers=headers,
        timeout=10,
    )
    assert add_resp.status_code in (200, 201), f"Agregar item falló: {add_resp.text}"
    item = add_resp.json()
    assert item["varianteId"] == variante_elegida["id"]
    assert item["cantidad"] == 1

    # 6. Aplicar cupón OTONO2026 (15% off)
    cup_resp = httpx.put(
        f"{base}/carritos/{carrito_id}/descuento",
        json={"codigo": "OTONO2026"},
        headers=headers,
        timeout=10,
    )
    assert cup_resp.status_code == 200, f"Aplicar cupón falló: {cup_resp.text}"

    # 7. Obtener total con descuento aplicado
    total_resp = httpx.get(f"{base}/carritos/{carrito_id}/total", headers=headers, timeout=10)
    total_con_descuento = float(total_resp.json()) if total_resp.status_code == 200 else None

    # 8. Checkout
    datos_envio = {
        "nombreDestinatario": "Comprador Test",
        "direccion": "Calle Prueba 123",
        "ciudad": "Mendoza",
        "provincia": "Mendoza",
        "codigoPostal": "5500",
        "telefono": "2615559999",
        "metodoPago": "TRANSFERENCIA",
    }
    checkout_resp = httpx.post(
        f"{base}/carritos/{carrito_id}/checkout",
        json=datos_envio,
        headers=headers,
        timeout=10,
    )
    assert checkout_resp.status_code in (200, 201), f"Checkout falló: {checkout_resp.text}"
    orden = checkout_resp.json()

    # 9. Verificar orden PENDIENTE con monto correcto (85% del precio de la variante)
    assert orden["estado"] == "PENDIENTE"
    assert orden["montoFinal"] > 0
    precio_variante = float(variante_elegida["precio"])
    monto_esperado = precio_variante * 0.85
    assert orden["montoFinal"] == pytest.approx(monto_esperado, rel=0.02), (
        f"Monto final esperado ~{monto_esperado:.2f}, obtenido {orden['montoFinal']}"
    )

    # 10. Verificar que el stock bajó en 1
    variante_post = httpx.get(f"{base}/variantes/{variante_elegida['id']}", timeout=10).json()
    assert variante_post["stock"] == stock_inicial - 1, (
        f"Stock esperado {stock_inicial - 1}, obtenido {variante_post['stock']}"
    )

    # 11. Verificar que el carrito quedó CONVERTIDO
    carritos_usuario = httpx.get(f"{base}/carritos", headers=headers, timeout=10).json()
    carrito_post = next((c for c in carritos_usuario if c["id"] == carrito_id), None)
    if carrito_post:
        assert carrito_post["estado"] == "CONVERTIDO", (
            f"Estado del carrito esperado CONVERTIDO, obtenido {carrito_post['estado']}"
        )
