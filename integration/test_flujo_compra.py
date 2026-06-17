"""
Flujo completo de compra:
registro → login → buscar producto con stock → crear carrito →
agregar item → aplicar cupón → checkout → verificar orden, stock y estado del carrito.
"""

import uuid

import httpx
import pytest

BACKEND_URL = None  # se resuelve en el fixture a través de conftest


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
    token = reg_resp.json()["token"]
    user_id = reg_resp.json()["id"]

    headers = {"Authorization": f"Bearer {token}"}

    # 2. Login verificado (token ya obtenido en registro)
    login_resp = httpx.post(f"{base}/auth/login", json={
        "username": reg_payload["username"],
        "password": reg_payload["password"],
    }, timeout=10)
    assert login_resp.status_code == 200
    token = login_resp.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Listar productos y tomar el primero con al menos una variante con stock
    productos = httpx.get(f"{base}/productos", timeout=10).json()
    assert len(productos) > 0, "No hay productos en el seed"

    variante_elegida = None
    producto_elegido = None
    for prod in productos:
        variantes_resp = httpx.get(f"{base}/variantes", params={"productoId": prod["id"]}, timeout=10)
        # El endpoint /variantes puede no filtrar por productoId; iteramos todas
        break

    # 4. Obtener variantes y buscar una con stock
    all_variantes = httpx.get(f"{base}/variantes", timeout=10).json()
    for v in all_variantes:
        if v.get("stock", 0) > 0:
            variante_elegida = v
            # Buscar el producto correspondiente
            prod_resp = httpx.get(f"{base}/productos/{v['productoId']}", timeout=10)
            if prod_resp.status_code == 200:
                producto_elegido = prod_resp.json()
            break

    assert variante_elegida is not None, "No hay variantes con stock"
    stock_inicial = variante_elegida["stock"]

    # 5. Crear carrito
    carrito_resp = httpx.post(f"{base}/carritos", json={"usuarioId": user_id}, headers=headers, timeout=10)
    assert carrito_resp.status_code in (200, 201)
    carrito = carrito_resp.json()
    assert carrito["estado"] == "ACTIVO"
    carrito_id = carrito["id"]

    # 6. Agregar variante al carrito
    add_resp = httpx.post(
        f"{base}/carritos/{carrito_id}/items",
        json={"idVariante": variante_elegida["id"], "cantidad": 1},
        headers=headers,
        timeout=10,
    )
    assert add_resp.status_code in (200, 201), f"Agregar item falló: {add_resp.text}"

    # 7. Aplicar cupón OTONO2026 (15% off)
    cup_resp = httpx.put(
        f"{base}/carritos/{carrito_id}/descuento",
        json={"codigo": "OTONO2026"},
        headers=headers,
        timeout=10,
    )
    assert cup_resp.status_code == 200, f"Aplicar cupón falló: {cup_resp.text}"

    # Obtener total con descuento para verificar más tarde
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

    # 9. Verificar orden PENDIENTE y monto con descuento
    assert orden["estado"] == "PENDIENTE"
    assert orden["montoFinal"] > 0
    precio_variante = variante_elegida["precio"]
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
