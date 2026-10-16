# T4 de sesión — stock compatible

Base: `691cdd5ae9feba5f4c7d050033219f33b179f331`. Rama exclusiva core.
Equivale a T5 histórica del PLAN Approved. CA-07/12/15/18 avanzados.

## Implementación

`application/ports.py`: CompatibleStockProvider; `application/stock.py`: snapshots
cacheados por clave exacta, únicamente durante una corrida. `infrastructure/stock_adapter.py`
consume el contrato público InventoryRepository y DTO de Inventory, nunca su
Infrastructure. Filtra tipo, espesor, estado y cantidad positiva. Prioridad:
RETAZO, PLANCHA; fecha DESC, ID DESC; índice físico ASC 1..cantidad para planchas,
1 para retazos. Identidad incluye fuente, ID e índice: no colisionan filas homónimas.
No se deduce encaje por AABB y se conserva la geometría irregular.

La consulta lógica por grupo usa una read_transaction y dos lecturas públicas de
catálogo, sin commit ni locks ni writes. Inventory no ofrece consulta batch filtrada;
no se inventa API SQL cross-module. Tradeoff documentado: se leen catálogos completos,
filtrados localmente. El cache por corrida evita repetir las lecturas de una clave;
una corrida nueva refresca disponibilidad. Optimizar el acceso SQL futuro requiere
un port filtrado acordado con Inventory, sin cambiar semántica del motor.
Dimensiones NUMERIC se convierten explícitamente al JSON canónico T1 solo si
Decimal(str(numero)) conserva el valor; se rechaza una conversión con pérdida.

## Validación

Desde backend, activar `source /workspace/.setup/runtime.sh`:

```bash
python -m pytest -q tests/unit/optimization/test_stock.py tests/integration/optimization/test_stock_adapter.py
python -m pytest -q tests/optimization tests/unit/optimization tests/api/optimization tests/integration/optimization tests/unit/inventory tests/api/inventory
```

**8 passed** focalizadas; **743 passed, 1 warning** regresión, sin skips/fallos.
Logs [focalizadas](logs/t4-focused.txt) y [regresión](logs/t4-regression.txt).
La prueba PostgreSQL real usa Inventory y tablas migradas en una BD temporal:
retazo #5 primero, plancha #5 índices 1/2, conserva cantidad=2 y estado del retazo;
0 movimientos creados. HU-015 sigue verde. Diff-check correcto antes del commit.

## Equipo y riesgos

[Refs observados](logs/t4-team.txt): mismos tips que T3; sin nuevos cambios externos.
Orders dd10ec0 contiene payload por pieza relacionado con 422; sin integrar ni
proclamar E2E corregido. RBAC dinámico y UI fixtures requieren convergencia posterior
según t3-preparation.md. HU-008 sigue antecedente histórico, sin heredar AABB/0–90
como aprobación final. Ninguna mutación del stock, migración ni cambio frontend.
PLAN sigue Approved; SPEC Reviewed intacta. No bloqueos materiales.
