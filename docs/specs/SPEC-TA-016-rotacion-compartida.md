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
