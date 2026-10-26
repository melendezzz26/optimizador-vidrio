# Auditoría angular — regla Sprint 2 de 5° (2026-10-26)

Rama feature/S2-rotation-best-fit. Antes de editar: working tree limpio.
Integration avanzó de 783aac8 a 6f2a159; incorporada por merge normal sin conflictos.
Los cambios entrantes son documentos HU-017/TA-021/TA-037 y benchmark TA-037.

## Fuentes identificadas antes de modificar valores

- domain/problem.py: OptimizationConfig requería angular_step_deg; no tenía default.
- infrastructure/configuration_seed.py: DEMO_PARAMETERS fijaba 90°.
- tests/optimization_e2e_data.py: fixture compartida por seed/demo/E2E fijaba 90°.
- infrastructure/run_uow.py: construye OptimizationConfig desde la única
  Configuracion vigente (paso_angular_grados). No hay fallback al seed.
- application/preparation y slices FF/BF reciben configuración del llamador.
- domain/packing.py: FF/BF/WF pasan exactamente problem.config.angular_step_deg
  a RasterCache.orientations. Ningún optimizador fija 90/45/15.
- application/runs.py: AcceptRun valida parámetros antes de preparar la ejecución.
- run_snapshot.py conserva/reconstruye la configuración de cada ejecución.
- metrics.py usa 360° deliberadamente para rasterizar a 0° un contorno YA rotado;
  no es granularidad de búsqueda. confirmation.py valida contra el paso del snapshot.
- HTTP RunRequestV1 admite solo order_ids, no parámetros angulares.
  ConfigV1 expone el paso efectivo en respuestas; UI no tiene selector angular.
  Fixtures frontend firstFitFixture.js y contractV1Fixture.json ya usan 5°.
- Hay 90° explícitos en tests de preparación, métricas, FF/WF y slices históricos;
  45° en pruebas de giro y límites comerciales; 15/45/90 en SP-003 y benchmark
  exploratorio TA-037. Son casos explícitos, no defaults operativos.
- models.py permite valores positivos <=360 y nullable para historia migrada;
  no se altera esa restricción ni el contrato de lectura histórica.

## Decisión aplicada

Constante SPRINT_2_ANGULAR_STEP_DEG = Decimal(5) en domain/problem.py.
OptimizationConfig usa 5° cuando no se proporciona paso; el seed nuevo usa
la misma constante. Fixture E2E y configuración de aceptación se alinean a 5°.
Motor genérico conserva el parámetro explícito para investigación/reproducción.
FF/BF/WF siguen compartiendo pack → RasterCache.orientations.

AcceptRun rechaza configuración vigente distinta de 5° con CONFIG_CONFLICT,
ANTES de lock_pending/create/transition. No sustituye silenciosamente el valor
de una versión persistida ni altera snapshots de ejecuciones previas.
El seed sigue preservando una vigente completa, incluso si es histórica de 90°.
Para ejecutar sobre una BD con ese valor, el responsable debe publicar una nueva
versión vigente de 5° por el proceso de configuración existente. No se ejecutó
seed, migración ni escritura en una BD real en este trabajo.

Secuencia antes de deduplicar: 0,5,...,355 (72 ángulos).
Círculos solo 0°, deduplicación de máscaras posterior y orden estable intactos.
BF conserva MIN(capacidad posterior) y el primer placement de cada fuente.
