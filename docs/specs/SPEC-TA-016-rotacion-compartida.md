# SPEC TA-016 — rotación compartida

Base técnica actualizada tras cambios integrados en PR #58 (783aac8).
Ver ../../docs/reviews/S2-PR58-rotation-best-fit.md.
Componente canónico: domain/rotation.py, RasterCache.orientations.
Entrada: PieceUnit, resolution_mm, angular_step_deg. Salida:
tuple[OrientedUnit], con Orientation(ángulo, geometría normalizada, máscara).

Generar múltiplos exactos del paso <360; normalizar ángulos; conservar orden;
deduplicar solo máscaras completas iguales, conservando primera geometría/ángulo.
Círculos a 0°. Preservar RN-04, límites y errores de precisión.
Sin selección de fuente, inventario, HTTP, SQLAlchemy ni Supabase.
pack es el único consumidor para FF/BF/WF; todos usan exactamente la misma ruta.

Aceptación: regresiones FF/rotation/WF antes y después sin cambios de placements;
prueba parametrizada de las tres heurísticas invocando el mismo componente.
No se exige una extracción adicional: PR58 ya centralizó el motor.

## Regla operativa Sprint 2 (2026-10-26)

Granularidad operacional compartida: **5°**. Secuencia ascendente 0,5,...,355
(72 ángulos), antes de deduplicación por máscara. Círculos solo 0°.
FF/BF/WF usan exactamente RasterCache.orientations a través de pack; sin
rotación exclusiva de BF. Se preservan normalización y pipeline raster.
OptimizationConfig y seed nuevos usan 5° por defecto. AcceptRun exige vigente
de 5°; los pasos explícitos alternativos siguen disponibles para spikes y
reproducción histórica. Ver docs/reviews/S2-angular-configuration.md.

## Caché acotada para pedidos con geometrías distintas

- Se conserva la cuadrícula del snapshot, incluida la operación a 1 mm. La
  regeneración usa el mismo ángulo, contorno normalizado y rasterizador.
- Cada cálculo tiene su propia caché. Al alcanzar 64 MiB contabilizados, libera
  referencias a orientaciones de pieza por orden de uso, comenzando por la menos
  reciente. Una máscara sigue consumiendo presupuesto mientras una base, un
  iterador, un candidato o un observador mantenga una referencia a ella.
- El stock y las bases de HU-017 siguen disponibles durante la ejecución. Los
  layouts y la frontera de M6 conservan su estado y sus límites independientes.
  El recambio de máscaras puede ocurrir entre dos colocaciones o durante la
  evaluación de una pieza, con el mismo orden, deduplicación exacta y desempates.
- Un conjunto activo que excede el límite produce un fallo técnico. L-13 valida
  las bases residentes y el límite en ejecución cubre los giros solicitados.
- La verificación compara geometrías, colocaciones y métricas con la caché
  anterior cuando ambas completan. Los casos grandes registran cobertura y
  causa de término para cada motor, con memoria y tiempo medidos por separado.
