# TA-016 / TA-018 — evidencia de cierre técnico

NewGlass, Sprint 2, Andro Quispe. Base técnica actualizada tras cambios integrados
en PR #58: 783aac89323a2780dc4b769e2a0603cd06490815.
Rama: feature/S2-rotation-best-fit. Sin rebase, sin PR ni merge a integration.

## Resultado

TA-016 reutiliza RasterCache.orientations; solo se añade documentación de su
contrato en código y pruebas comunes. FF, BF y WF llaman a pack y comparten
exactamente generación de orientaciones, máscaras, posiciones y validación.
No fue necesaria otra extracción: PR58 ya había creado el motor compartido.

BF implementado en domain/best_fit.py y application/best_fit.py (simulación).
Usa FeasibleCandidate y remaining_free_cells_after_placement de PR58.
Minimiza (capacidad libre posterior en celdas, stock_rank, orientation_rank,
row, column). Solo compara fuentes del mismo nivel; prioridad retazo obligatoria.
La capacidad contempla margen, interior material y halo de separación.
BF no busca una posición ni una orientación mejor dentro de cada fuente.

BestFitResult conserva método BF después de calculate_metrics. El contrato
durable/HTTP sigue siendo FF, como en la integración existente de WF: no se
añade confirmación automática ni endpoint BF en este frente.

## Pruebas y límites

Ver backend-tests.txt: línea base 80; después 101 (80 existentes + 21 nuevas).
Pruebas nuevas en tests/unit/optimization/test_best_fit.py y
tests/integration/optimization/test_best_fit_slice.py: normal, rotación,
no colocable, tuple de desempate, reproducibilidad/eventos, prioridad retazo,
fallback, unidades físicas, capacidad posterior con separación, material irregular,
primer placement, métricas y ausencia de mutación de inventario.
La prueba SQLite usa repositorios reales y compara snapshots de TODAS las tablas.

Suite completa: 1445 passed, 605 skipped, 1 warning. Las omitidas requieren
binarios PostgreSQL locales, no disponibles. No se ejecutó frontend: no hay
cambios de UI. SQLite no sustituye validación de concurrencia/constraints PostgreSQL.
No se modificó ni debilitó ninguna prueba de PR58.

## Investigación

Auditoría completa: docs/reviews/S2-PR58-rotation-best-fit.md.
SP-003: docs/spikes/SP-003-pasos-angulares.md, script versionado y results.json.
90/45/15 grados; misma entrada, FF, raster, margen, separación y orden.
45 grados recomendado solo para esta instancia; no se cambia el default.

## Archivos de implementación

- domain/rotation.py: contrato compartido documentado, algoritmo intacto.
- domain/problem.py: Literal incluye BF.
- domain/best_fit.py: selector, optimizador, identidad de resultado.
- application/best_fit.py: preparación y stock de solo lectura.
- tests/unit/optimization/test_best_fit.py: comportamiento y componente común.
- tests/integration/optimization/test_best_fit_slice.py: snapshot BD intacto.

SPEC/PLAN/TASKS de TA-016 y TA-018 están en docs/specs.
## Git y publicación

HEAD inicial/final observado de integration: 783aac8. Ningún commit pendiente
de integration al terminar la implementación; se ejecutó fetch --prune.
La feature se creó desde esa base actualizada mediante fast-forward local.
Commits: 77763ad (auditoría/SP-003/diseño), c8acf26 (implementación/pruebas),
más el commit de cierre que contiene esta evidencia y normalización documental.
Push inicial de rama y push de ambos commits confirmados por Git hacia
origin = https://github.com/melendezzz26/optimizador-vidrio.git.
La revisión automática inicialmente bloqueó la publicación; al aportar el
alcance explícitamente autorizado y verificar que el payload contiene únicamente
código, documentación y datos sintéticos, permitió el push.

git diff --check aprobado después de normalizar finales de archivos de documentación.
No PR, no rebase, no merge a integration. Simulación BF sin escrituras de inventario.
El HEAD definitivo y estado limpio se comprueban después del commit de cierre.
