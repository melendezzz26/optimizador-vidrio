# HU-014 — comandos y resultados de pruebas

Estos son comandos reproducibles. Ejecutar los comandos de backend desde `backend/` y los de frontend/E2E desde `frontend/`. Los resultados siguientes corresponden a la ejecución reportada para la rama y el HEAD funcional `83cedbe`; no se volvieron a ejecutar en el cierre documental.

## Backend

```powershell
python -m pytest tests/api/inventory -q
python -m pytest tests/unit/inventory -q
python -m pytest tests/integration/inventory -q
python -m pytest tests -q
```

Resultados reportados:

| Suite | Resultado |
|---|---:|
| Inventory API | 46 passed |
| Inventory unit | 350 passed |
| Inventory integration | 59 passed |
| Backend completo | 1181 passed |

Entorno: Windows, Python 3.11.9 y PostgreSQL aislado para integración. La advertencia `StarletteDeprecationWarning` / `httpx` fue reportada como no bloqueante. La migración HU-014 se verificó en PostgreSQL aislado; no ejecutar estos comandos contra Supabase.

## Frontend

```powershell
npm run test:unit
npm run test:component
npm run lint
npm run build
```

Resultados reportados:

| Comando | Resultado |
|---|---:|
| `npm run test:unit` | 84/84 PASS |
| `npm run test:component` | 166/166 PASS |
| `npm run lint` | PASS |
| `npm run build` | PASS |

## E2E HU-014

```powershell
npx playwright test tests/e2e/hu014-inventory-writeoff.spec.js
```

Resultado reportado: **3 passed, 1 skipped, 0 failed**. La baja real usa una única plancha del fixture y se ejecuta solo en desktop para evitar repetir una baja única en el mismo recurso. El test de permisos corre en desktop y mobile; el skip del flujo mutante en mobile es intencional, no un fallo.

La suite E2E global también se ejecutó y contiene fallos de HU-007. No está verde; esos fallos son deuda externa a HU-014 y requieren revisión separada.

## Calidad documental

```powershell
git diff --check
```

Resultado reportado para este cierre documental: **PASS**. Esta carpeta contiene únicamente el resumen reproducible; no se generaron logs ni reportes de prueba artificiales.
