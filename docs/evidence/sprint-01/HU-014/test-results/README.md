# HU-014 — comandos y resultados de pruebas

Estos son comandos reproducibles. Ejecutar los comandos de backend desde `backend/` y los de frontend/E2E desde `frontend/`. Los resultados pre-merge abajo se conservan como referencia histórica de `83cedbe`. Los resultados post-merge se separan para no atribuir a `01d84f9` ejecuciones anteriores.

## Backend

```powershell
python -m pytest tests/api/inventory -q
python -m pytest tests/unit/inventory -q
python -m pytest tests/integration/inventory -q
python -m pytest tests -q
```

Resultados reportados antes del merge `01d84f9`:

| Suite | Resultado |
|---|---:|
| Inventory API | 46 passed |
| Inventory unit | 350 passed |
| Inventory integration | 59 passed |
| Backend completo | 1181 passed |

Entorno: Windows, Python 3.11.9 y PostgreSQL aislado para integración. La advertencia `StarletteDeprecationWarning` / `httpx` fue reportada como no bloqueante. La migración HU-014 se verificó en PostgreSQL aislado; no ejecutar estos comandos contra Supabase.

Resultados post-merge de backend y Alembic:

| Comando | Resultado post-merge |
|---|---|
| `.\venv\Scripts\python.exe -m pytest tests -q` | **1207 passed, 1 warning**, 258.92 s. `StarletteDeprecationWarning` de FastAPI/Starlette `TestClient`, no bloqueante. |
| `.\venv\Scripts\python.exe -m alembic heads` | `fa014e1a2b3c (head)`; un único head. |

## Frontend

```powershell
npm run test:unit
npm run test:component
npm run lint
npm run build
```

Resultados reportados antes del merge `01d84f9`:

| Comando | Resultado |
|---|---:|
| `npm run test:unit` | 84/84 PASS |
| `npm run test:component` | 166/166 PASS |
| `npm run lint` | PASS |
| `npm run build` | PASS |

Resultados post-merge de frontend:

| Comando | Resultado post-merge |
|---|---|
| `npm run test:unit` | **84 passed, 0 failed**. |
| `npm run test:component` | **19 test files passed; 205 tests passed, 0 failed**. |
| `npm run lint` | **PASS**. |
| `npm run build` | **PASS**; Vite 8.3.1, 1941 modules transformed. |

## E2E HU-014

```powershell
npx playwright test tests/e2e/hu014-inventory-writeoff.spec.js
```

Resultado reportado: **3 passed, 1 skipped, 0 failed**. La baja real usa una única plancha del fixture y se ejecuta solo en desktop para evitar repetir una baja única en el mismo recurso. El test de permisos corre en desktop y mobile; el skip del flujo mutante en mobile es intencional, no un fallo.

Suite E2E completa post-merge:

```powershell
npm run test:e2e
```

Resultado informado: **31 passed, 1 skipped, 0 failed**. El único skip corresponde al escenario de baja HU-014 en `chromium-mobile` porque el fixture contiene una sola plancha susceptible de una única baja manual. El escenario de permisos se ejecuta en desktop y mobile. No se registra deuda vigente de HU-007 en esta rama tras la integración.

## Calidad documental

```powershell
git diff --check
```

Resultado post-merge de este ajuste documental: **PASS** (`git diff --check`). Esta carpeta contiene únicamente el resumen reproducible; no se generaron logs ni reportes de prueba artificiales.
