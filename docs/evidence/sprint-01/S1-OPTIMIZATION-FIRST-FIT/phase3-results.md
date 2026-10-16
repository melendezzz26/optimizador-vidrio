# Resultado reconstruible y métricas FF

Base publicada `f63ae3e275df7b77f4ee4636c2da247b629624f4`.
Objetivo: resultado T8 histórico del PLAN, antes de transporte y confirmación.

Archivos: `domain/metrics.py`, `application/calculation.py`, puertos/UoW y pruebas
`test_metrics.py`, `test_runs.py`; PLAN. Se elimina whitespace heredado del snapshot
ORM histórico, detectado por el diff-check con archivos nuevos ya staged.

## Decisiones y resultado

- Reutiliza First Fit real; JSONB conserva problema/candidatos/unidades/geometrías,
  Decimal string, configuración/version/mínimos, placements, métricas y residuales.
- Consulta durable reconstruye dataclasses y valida asociación sin ejecutar FF.
- Una fila FF; materiales propuestos agregados por fuente/ID y unidades físicas;
  métricas R4 si denominador>0; sin colocaciones metrics=null y ninguna fila R4.
- Rectángulo residual máximo EXACTO entre celdas interiores, margen/separación y
  ocupación; stack monótono y desempate §8, check geométrico repetido. No es AABB.
  Solo se guarda propuesta con dimensiones y origen; no se crea ningún Retazo.
- Aprovechamiento HALF_UP a 3 decimales; merma = área usada − piezas − recuperable.
  No clamps que oculten inconsistencias. No mínimo de área inventado.
- Reloj motor/métricas excluye DB/stock, callbacks (incluyendo esperas de red),
  serialización y persistencia. Prueba de reloj controlado: 7ms de cálculo,
  aunque se agreguen segundos ficticios de I/O/entrega.
- Estado final y N pedidos comparten el commit del resultado para mantener
  coherencia desde este bloque; auditoría reforzada de fallos en bloque estados.

## Verificación

```bash
# backend, PostgreSQL exclusivamente local
python -m pytest tests/optimization tests/unit/optimization tests/api/optimization tests/integration/optimization tests/api/authorization tests/integration/test_s1_rbac_migration.py tests/integration/test_staging_bootstrap.py tests/integration/test_clients_migration.py -q
git diff --cached --check
```

**508 passed, 1 warning**. Incluye 22 pruebas de métricas/multipedido/resultados.
Se comprobó algoritmo de rectángulos contra brute force para las 512 máscaras 3×3,
material irregular, mínimos, margen/separación, timer, reconstrucción sin motor,
rollback final, resultados completos/parciales/vacíos y Decimal de coordenadas.

Ejemplo real: 2 pedidos × 2 piezas 2×2mm, plancha ID5 4×2mm cantidad2:
placements `(unit1,x0,y0)`, `(unit1,x2,y0)`, `(unit2,x0,y0)`, `(unit2,x2,y0)`;
4/4, 100%, dos unidades físicas usadas. Stock permanece cantidad2, movimientos0.
Caso Decimal: dos tiras 0.25×2mm en 4×2mm, x=0 y0.250; residual exacto3.5×2mm,
recuperable7mm², sin alta de retazo.

CA avanzados: 12,15,16,17,18,19 (sin confirmación). HU-015/RBAC verdes.
UI observada `4a3c9c1`; sin cambios externos ni integración UI/Orders.
Alembic continúa única `s1opt02b4c6d`. Riesgos pendientes: recuperación operacional,
confirmación, mínimos de área y concurrencia final se abordan en bloque separado.
