# Cumbre E-commerce — Test Suite

Suite de pruebas para el backend Spring Boot y el frontend React de **Cumbre**.
Organizada en tres niveles: **API**, **integración** y **E2E**.

---

## Prerequisitos

- Python 3.11+
- Backend Spring Boot corriendo en `http://localhost:8080` (perfil `local`, base H2 con seed)
- Frontend React corriendo en `http://localhost:5173` (solo para tests E2E)

---

## Instalación

```bash
# Clonar e instalar dependencias
pip install -e .

# Instalar browsers de Playwright
playwright install chromium
```

## Configuración

Copiar el archivo de ejemplo y ajustar las URLs si el entorno es distinto al default:

```bash
cp .env.example .env
```

Variables disponibles:

| Variable | Default |
|---|---|
| `BACKEND_URL` | `http://localhost:8080/api` |
| `FRONTEND_URL` | `http://localhost:5173` |

---

## Levantar los servicios

### Backend

```bash
# Desde el directorio del proyecto Spring Boot
./mvnw spring-boot:run -Dspring-boot.run.profiles=local
```

El backend debe estar disponible en `http://localhost:8080` con la base H2 en memoria
y los datos seed cargados (usuarios, productos, variantes, descuentos).

### Frontend (solo E2E)

```bash
# Desde el directorio del proyecto React
npm run dev
```

El frontend debe estar disponible en `http://localhost:5173`.

---

## Correr los tests

### Solo tests de API (no requieren frontend)

```bash
pytest -m api
```

### Solo tests de integración

```bash
pytest -m integration
```

### Solo tests E2E (requieren frontend y backend)

```bash
pytest -m e2e
```

### Todos los tests

```bash
pytest
```

### Con reporte HTML

```bash
pytest --html=report.html --self-contained-html
```

### Con salida detallada y parar al primer fallo

```bash
pytest -m api -v -x
```

### Tests E2E en modo headful (ver el browser)

```bash
pytest -m e2e --headed
```

### Tests E2E en un browser específico

```bash
pytest -m e2e --browser firefox
pytest -m e2e --browser webkit
```

---

## Estructura

```
cumbre-tests/
├── pyproject.toml          # dependencias del proyecto
├── pytest.ini              # marks y configuración de pytest
├── .env.example            # variables de entorno
├── conftest.py             # fixtures globales (HTTP clients, Playwright pages)
├── api/
│   ├── test_auth.py        # login, registro, endpoints protegidos
│   ├── test_productos.py   # CRUD productos, filtros por estado/categoría/marca
│   ├── test_carrito.py     # crear carrito, agregar/actualizar/eliminar items, cupones
│   ├── test_checkout.py    # flujos de checkout, descuento en monto, stock
│   ├── test_ordenes.py     # permisos de órdenes, confirmar, cancelar
│   ├── test_descuentos.py  # activos, buscar por código, CRUD admin
│   └── test_admin.py       # dashboard, categorías, marcas, contacto
├── integration/
│   ├── test_flujo_compra.py   # flujo completo registro → checkout → verificar stock
│   └── test_flujo_admin.py    # flujo admin: crear catálogo → pausar → eliminar
└── e2e/
    ├── test_registro_login.py  # validaciones de form, redirect según rol
    ├── test_catalogo.py        # filtros, búsqueda, detalle, agregar al carrito
    ├── test_compra.py          # flujo E2E completo hasta /confirmacion
    └── test_admin_panel.py     # panel admin: CRUD productos y cupones, vistas
```

---

## Usuarios seed

| Username | Password | Rol |
|---|---|---|
| `admin` | `admin123` | ADMIN |
| `juanperez` | `user123` | CLIENTE |
| `mariagomez` | `cliente123` | CLIENTE |

## Descuentos seed

| Código | Tipo | Valor | Vence |
|---|---|---|---|
| `OTONO2026` | PORCENTAJE | 15% | 2026-06-30 |
| `FIJO5000` | FIJO | $5000 | 2026-12-31 |

---

## Notas de diseño

- Cada test es **independiente**: no depende del orden de ejecución ni del estado dejado por otro test.
- Los recursos creados en tests de API usan `uuid4` para evitar colisiones entre ejecuciones.
- Los tests de integración usan `httpx` directamente (sin fixtures de pytest) para controlar el flujo completo.
- Los tests E2E nunca usan `time.sleep()` — usan `expect(...).to_be_visible(timeout=N)` de Playwright.
