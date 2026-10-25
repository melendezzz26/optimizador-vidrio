# Auditoría POST-PR58 — NewGlass / Andro Quispe

Base técnica actualizada tras cambios integrados en PR #58.
HEAD inicial de origin/integration/sprint-01 y base feature:
783aac89323a2780dc4b769e2a0603cd06490815.
Primer padre: 0943f95; segundo: cf5a4e0.
Commits incorporados: e7ef17c (diseño), 81f0b23 (motor),
fc501a3 (pruebas), cf5a4e0 (evidencia).
Auditoría realizada mediante diff del primer padre contra el merge, no solo mensajes.

## Antes del cambio vs estado actual

| Aspecto | Antes (0943f95) | Actual (783aac8) |
|---|---|---|
| Archivos nuevos | Sin packing ni WF | domain/packing.py y domain/worst_fit.py |
| First Fit | Bucle completo en first_fit.py | Wrapper de pack; conserva imports de helpers/evento |
| Candidato | Placement construido al aceptar | FeasibleCandidate inmutable con layout y score diferidos |
| Posiciones | SheetLayout.first_position | Mismo método, primera fila/columna factible |
| Exploración | Fuente, orientación, fila, columna | Misma exploración, generador por tipo de fuente |
| Rotación | RasterCache.orientations | Sin cambios en rotation.py |
| Raster | TA-005/006 | Sin cambios en rasterizador ni máscaras |
| Stock compatible | Adapter/puerto de lectura | Sin cambios; pack preserva orden recibido por tipo |
| Retazo → plancha | Orden estable prioriza retazos | Dos niveles explícitos; sin comparar entre niveles |
| Placement | Contrato inmutable | Sin cambios; problem.py amplía Literal del método con WF |
| Determinismo | Orden preparación/stock/ángulos/posiciones | Conservado; WF agrega score y ranks estables |
| Métricas | calculate_metrics externo | Sin cambios; capacidad raster nueva NO sustituye métricas |
| Reutilización | Rotación y geometría ya comunes | pack, FeasibleCandidate, capacidad y primer placement por fuente |
| Extracción pendiente | Se podía extraer el bucle de FF | PR58 ya lo hizo; TA-016 formaliza rotación existente |
| Pruebas nuevas | FF/rotación previos | test_worst_fit.py, test_worst_fit_slice.py (incluye regresión FF) |

Otros archivos nuevos de PR58:
docs/specs/SPEC-TA-019-worst-fit.md, PLAN-TA-019-worst-fit.md;
docs/evidence/sprint-02/TA-019/{README.md,backend-tests.txt,diff-check.txt}.
No se eliminan ni debilitan esas pruebas.

## Pipeline y responsabilidades

application.preparation.prepare_persisted_problem → domain.preparation.prepare_problem
expande PieceUnit y ordena (-área, -lado mayor, pedido, pieza, unidad).
application.stock.with_compatible_stock usa CompatibleStockProvider; InventoryStockAdapter
lee inventario compatible. Su orden vigente es fecha_registro e ID descendentes
y luego unidad física; pack conserva ese orden (stock_rank), sin crear timestamps nuevos.
Los timestamps persistidos ya forman parte del orden upstream; BF no los consulta ni genera.

pack → RasterCache.orientations → discrete_angles / oriented_geometry →
_raster → rasterize_geometry → Orientation(mask, geometry, rotation_deg).
Material: RasterCache.material → rasterize_material → _empty_layout.
_feasible_candidates filtra bbox y llama SheetLayout.first_position
(validación por bits, margen y separación); emite solo primer placement por fuente.
FF toma next; WF maximiza capacidad; BF minimizará la MISMA capacidad.
pack aplica únicamente layout_after ganador y construye Placement.
calculate_metrics revalida geometría y produce propuestas de retazos sin persistirlas.

La deduplicación actual compara máscara completa (columnas, filas de bits),
conserva el primer ángulo; no itera el set. Círculos solo 0°.
Ángulos ascendentes menores de 360°, cuarto de vuelta exacto, RN-04 seis decimales.
Cache por cálculo; límites de memoria y geometría vigentes conservados.

## Decisión

No crear otra abstracción de candidato, raster ni rotación.
TA-016 adopta rotation.py y su contrato existente para FF/BF/WF.
TA-018 será selector sobre pack, con identidad BF en resultado de dominio.
Como WF integrado, no habilita un método HTTP ni confirmación BF implícita.
La simulación usa snapshots y puertos de lectura; no tiene acceso a escrituras.
