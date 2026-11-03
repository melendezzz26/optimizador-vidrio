# PLAN-TA-053 T01 - M6 Beam Search acotada

## Informacion general

| Campo | Valor |
|---|---|
| Estado | Completed for T01 |
| SPEC | [SPEC-TA-053-T01-M6-Beam-Search.md](SPEC-TA-053-T01-M6-Beam-Search.md) |
| Base | `origin/integration/sprint-01` |
| Rama | `feature/TA-053-m6-beam-search-integrated` |
| Dependencia | SP-006, commits experimentales trasladados sin cambios |

Este plan sigue la convencion de PLANs en `docs/specs/`. Cada tarea define
objetivo, archivos, pruebas, terminacion y riesgo. No modifica el coordinador
publico ni los motores existentes.

## T01.1 - Preparacion del modulo

- **Objetivo:** ubicar M6 junto a los optimizadores de dominio y exponer una
  funcion de application independiente.
- **Archivos previstos:** `backend/app/modules/optimization/domain/beam_search.py`,
  `backend/app/modules/optimization/application/beam_search.py`, y sus
  `__init__` solo si el estilo existente lo requiere.
- **Dependencias:** `problem`, `packing`/`placement`, `run_geometry`,
  `preparation`, `metrics` y `ports`.
- **Pruebas:** imports, contrato de resultado y aislamiento de imports.
- **Terminado:** M6 puede construirse sin importar coordinador, HTTP, ORM o
  experimentos.
- **Riesgo:** acoplamiento accidental a FF/BF/WF; revisar imports y diff.

## T01.2 - Estados parciales

- **Objetivo:** representar nodo, score y layouts por fuente.
- **Implementacion:** dataclasses congeladas; score lexicografico exacto de la
  SPEC; estimacion conservadora de memoria antes de reservar la frontera.
- **Pruebas:** inmutabilidad, desempates, fuentes no usadas y estado vacio.
- **Terminado:** cada placement crea layouts nuevos y el nodo previo no cambia.
- **Riesgo:** retener raster innecesario; medir y aplicar el limite configurado.

## T01.3 - Generacion de alternativas

- **Objetivo:** generar ramas por fuente, orientacion y posiciones primera/ultima.
- **Implementacion:** reutilizar `PreparedRunGeometry`, orientaciones deduplicadas,
  `SheetLayout.first_position`, `check` y `place`; retazos antes de planchas.
- **Pruebas:** rectangulo, circulo, poligono, giro de 5 grados, margen,
  separacion, retazo factible y fallback a plancha.
- **Terminado:** un nivel recorre todas las fuentes del tier antes de podar.
- **Riesgo:** convertir interrupcion de sondeo en falso NO_FIT; propagar limite.

## T01.4 - Evaluacion y poda

- **Objetivo:** implementar el score experimental y BS-k con `k=2`.
- **Implementacion:** ordenar establemente, conservar 12 hijos por padre y los
  mejores `k` globales; conservar la frontera anterior hasta cerrar el nivel.
- **Pruebas:** determinismo, traza, poda, empate y diferencia frente a FF/BF/WF.
- **Terminado:** ninguna llamada a los optimizadores base.
- **Riesgo:** cambiar silenciosamente el orden experimental; comparar trazas.

## T01.5 - Terminacion y resultados

- **Objetivo:** devolver resultado completo, parcial o sin colocaciones con
  razon de parada explicita.
- **Implementacion:** `OptimizationResult` comun; estado parcial no confirmable;
  limites diferenciados de imposibilidad geometrica.
- **Pruebas:** NO_FIT, limite de expansiones, sondeos, tiempo y memoria.
- **Terminado:** no se presentan resultados incompletos como completos.
- **Riesgo:** frontera vacia tras un nivel; definir fallback a la ultima
  frontera valida y cubrirlo con prueba.

## T01.6 - Pruebas fundamentales

- **Objetivo:** demostrar reglas, paridad y no regresion.
- **Archivos previstos:** `backend/tests/unit/optimization/` para algoritmo y
  `backend/tests/optimization/` para fixtures/reglas, siguiendo los directorios
  existentes.
- **Casos:** SMALL, MEDIUM, COMPLEX; tres geometrias; multiples fuentes y
  materiales; no-fit; determinismo; inventario inmutable; limites.
- **Ejecucion:** pruebas backend focalizadas en Windows y, para supervisor,
  recursos y PostgreSQL si fueran necesarios, los scripts oficiales en WSL2.
- **Terminado:** evidencia de cada criterio de aceptacion y `git diff --check`.
- **Riesgo:** confundir evidencia local del experimento con paridad backend;
  registrar ambas por separado.

## T01.7 - Evidencias y cierre

- **Objetivo:** conservar trazabilidad entre SPEC, PLAN, implementacion y
  resultados.
- **Archivos previstos:** evidencia TA-053 solo si las pruebas realmente se
  ejecutan; no alterar los artefactos de SP-006.
- **Pruebas:** lint/type-check aplicable, suite focalizada, regresiones FF/BF/WF.
- **Terminado:** diff limitado a TA-053, commits Conventional Commits con
  staging explicito, arbol limpio y sin push.
- **Riesgo:** incluir P0, M4, M5 o cambios de coordinador; revisar `git diff`
  contra `origin/integration/sprint-01`.

## Matriz de cobertura

| Requisito | Tarea |
|---|---|
| RF-01, RF-10 | T01.1, T01.5 |
| RF-02, RF-03, RF-04, RF-05 | T01.3, T01.6 |
| RF-06, RF-07 | T01.3, T01.4, T01.6 |
| RF-08 | T01.5, T01.6 |
| RF-09 | T01.2, T01.6 |
| Limites y memoria | T01.2, T01.4, T01.5, T01.6 |
| No regresion FF/BF/WF | T01.6, T01.7 |

## Resultado de ejecucion

T01.1 a T01.7 estan implementadas para el alcance de esta rama. La validacion
real del cierre de T01 incluyo:

- 495 pruebas de `unit/optimization` sin el runner supervisado en Windows.
- 861 pruebas de unidades, integracion y API en WSL2 con PostgreSQL aislado.
- 14 pruebas de `test_comparison_runner.py` en WSL2.
- 47 pruebas del experimento SP-006.
- `compileall` y `git diff --check`.

Las pruebas del runner no se consideran validas en Windows porque el
repositorio exige Linux/procfs/RLIMIT_AS/prctl; se ejecutaron y pasaron en
WSL2. No se altero el coordinador publico, FF/BF/WF, M4, M5, frontend,
persistencia ni inventario.

Estos conteos son historicos del cierre de T01, antes de ampliar la bateria en
T02. Los conteos vigentes de T02 son 19 pruebas focalizadas M6, 508 de
unit/optimization en Windows, 874 de unit/integration/API en WSL2, 14 del
runner y 47 de SP-006; el detalle se conserva en la
[evidencia TA-053 T02](../evidence/sprint-02/TA-053-T02/README.md). Son suites
solapadas y no se suman.
