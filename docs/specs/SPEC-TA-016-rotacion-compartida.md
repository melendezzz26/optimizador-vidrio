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

