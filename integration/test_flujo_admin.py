"""
Flujo completo admin:
login → crear categoría → marca → producto → variantes (con todos los campos requeridos)
→ actualizar → pausar → crear descuento → verificar con cliente → eliminar producto.

Campos requeridos por VarianteProductoRequest:
  productoId, color, talla, material, peso (BigDecimal), stock, precio, estacion (Enum)
"""

import uuid
from datetime import date, timedelta

import httpx
import pytest


def _backend_url():
    import os
    from dotenv import load_dotenv
    load_dotenv()
    return os.getenv("BACKEND_URL", "http://localhost:8080/api")


def _login_headers(base: str, username: str, password: str) -> dict:
    resp = httpx.post(f"{base}/auth/login", json={"username": username, "password": password}, timeout=10)
    resp.raise_for_status()
    return {"Authorization": f"Bearer {resp.json()['token']}"}


@pytest.mark.integration
def test_flujo_admin_completo():
    base = _backend_url()
    admin_h = _login_headers(base, "admin", "admin123")
    cliente_h = _login_headers(base, "juanperez", "user123")

    suffix = uuid.uuid4().hex[:6]

    # 2. Crear categoría nueva
    cat_resp = httpx.post(
        f"{base}/categorias",
        json={"nombre": f"CatTest {suffix}", "descripcion": "Categoría de prueba"},
        headers=admin_h,
        timeout=10,
    )
    assert cat_resp.status_code in (200, 201), f"Crear categoría falló: {cat_resp.text}"
    categoria_id = cat_resp.json()["id"]

    # 3. Crear marca nueva
    marca_resp = httpx.post(
        f"{base}/marcas",
        json={"nombre": f"MarcaTest {suffix}", "descripcion": "Marca de prueba"},
        headers=admin_h,
        timeout=10,
    )
    assert marca_resp.status_code in (200, 201), f"Crear marca falló: {marca_resp.text}"
    marca_id = marca_resp.json()["id"]

    # 4. Crear producto
    prod_resp = httpx.post(
        f"{base}/productos",
        json={
            "nombre": f"ProdAdmin {suffix}",
            "descripcion": "Producto de prueba del flujo admin",
            "marcaId": marca_id,
            "categoriaId": categoria_id,
            "precioBase": 30000.0,
            "estado": "ACTIVO",
        },
        headers=admin_h,
        timeout=10,
    )
    assert prod_resp.status_code in (200, 201), f"Crear producto falló: {prod_resp.text}"
    producto = prod_resp.json()
    producto_id = producto["id"]

    # 5. Crear dos variantes (todos los campos requeridos: color, talla, material, peso, stock, precio, estacion)
    for talla in ("S", "M"):
        var_resp = httpx.post(
            f"{base}/variantes",
            json={
                "productoId": producto_id,
                "color": "Negro",
                "talla": talla,
                "material": "Ripstop Nylon",
                "peso": 0.5,
                "stock": 5,
                "precio": 30000.0,
                "estacion": "INVIERNO",
            },
            headers=admin_h,
            timeout=10,
        )
        assert var_resp.status_code in (200, 201), f"Crear variante {talla} falló: {var_resp.text}"

    # 6. Verificar producto aparece en GET /productos/estado/ACTIVO
    activos_resp = httpx.get(f"{base}/productos/estado/ACTIVO", headers=admin_h, timeout=10)
    assert activos_resp.status_code == 200
    ids_activos = [p["id"] for p in activos_resp.json()]
    assert producto_id in ids_activos, "El producto recién creado no aparece en ACTIVO"

    # 7. Actualizar precio del producto
    precio_nuevo = 35000.0
    upd_payload = {**producto, "precioBase": precio_nuevo, "marcaId": marca_id, "categoriaId": categoria_id}
    upd_resp = httpx.put(f"{base}/productos/{producto_id}", json=upd_payload, headers=admin_h, timeout=10)
    assert upd_resp.status_code == 200, f"Actualizar producto falló: {upd_resp.text}"
    assert upd_resp.json()["precioBase"] == precio_nuevo

    # 8. Pausar producto y verificar que no aparece en lista pública
    pause_payload = {**upd_resp.json(), "estado": "PAUSADO", "marcaId": marca_id, "categoriaId": categoria_id}
    pause_resp = httpx.put(f"{base}/productos/{producto_id}", json=pause_payload, headers=admin_h, timeout=10)
    assert pause_resp.status_code == 200, f"Pausar producto falló: {pause_resp.text}"
    assert pause_resp.json()["estado"] == "PAUSADO"

    publicos = httpx.get(f"{base}/productos", timeout=10).json()
    ids_publicos = [p["id"] for p in publicos]
    assert producto_id not in ids_publicos, "Producto PAUSADO no debería aparecer en la lista pública"

    # 9. Crear descuento tipo PORCENTAJE
    hoy = date.today()
    desc_payload = {
        "nombre": f"Desc {suffix}",
        "codigo": f"DESC{suffix.upper()}",
        "tipo": "PORCENTAJE",
        "valor": 20.0,
        "fechaInicio": hoy.isoformat(),
        "fechaFin": (hoy + timedelta(days=60)).isoformat(),
        "estado": "ACTIVO",
    }
    desc_resp = httpx.post(f"{base}/descuentos", json=desc_payload, headers=admin_h, timeout=10)
    assert desc_resp.status_code in (200, 201), f"Crear descuento falló: {desc_resp.text}"
    descuento_codigo = desc_resp.json()["codigo"]

    # 10. Cliente puede buscar el descuento creado
    buscar_resp = httpx.get(
        f"{base}/descuentos/buscar",
        params={"codigo": descuento_codigo},
        headers=cliente_h,
        timeout=10,
    )
    assert buscar_resp.status_code == 200, f"Cliente no pudo buscar descuento: {buscar_resp.text}"
    data = buscar_resp.json()
    descuento_encontrado = data[0] if isinstance(data, list) else data
    assert descuento_encontrado["codigo"] == descuento_codigo

    # 11. Eliminar el producto
    reactive_payload = {**pause_resp.json(), "estado": "ACTIVO", "marcaId": marca_id, "categoriaId": categoria_id}
    httpx.put(f"{base}/productos/{producto_id}", json=reactive_payload, headers=admin_h, timeout=10)

    del_resp = httpx.delete(f"{base}/productos/{producto_id}", headers=admin_h, timeout=10)
    assert del_resp.status_code in (200, 204), f"Eliminar producto falló: {del_resp.text}"

    # 12. Verificar que aparece en GET /productos/estado/ELIMINADO
    elim_resp = httpx.get(f"{base}/productos/estado/ELIMINADO", headers=admin_h, timeout=10)
    assert elim_resp.status_code == 200
    ids_elim = [p["id"] for p in elim_resp.json()]
    assert producto_id in ids_elim, "Producto eliminado no aparece en estado/ELIMINADO"
