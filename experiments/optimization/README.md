# TA-027 — Entradas congeladas

Baseline: [SP-002](../../docs/evidence/sprint-02/SP-002/README.md).
Exactamente tres casos; versión de esquema 1. JSON es la fuente de verdad, no stock en vivo.
Las dimensiones son mm, áreas mm²; coordenadas de polígonos en orden perimetral.
IDs de vidrio 1 y 2 representan materiales sintéticos distintos; espesores 6 y 8 mm.
No requieren catálogo ni base de datos. Todos los pedidos tienen ID 1.

`loader.load_problem(case_id)` devuelve una reconstrucción nueva y profundamente inmutable.
La preparación productiva valida las piezas y las agrupa; el stock congelado conserva el orden
JSON dentro de cada nivel y expande `quantity` a índices físicos 1..N. Cada retazo tiene cantidad 1.
Las áreas se derivan de geometría con GeometryValidator y redondeo HALF_UP a 0.01 mm²,
como los snapshots persistidos; no son un parámetro ajustable del experimento.
Los cuatro parámetros de OptimizationConfig están explícitos. `rotation_allowed=true`
documenta que el motor rota todas las piezas; no existe un switch por pieza en este baseline.
Los límites residuales explícitos se usan solo en la revalidación común de métricas.

Desde `backend`, con Python del entorno del proyecto:

```text
python -m pytest tests/unit/optimization/test_experimental_cases.py -q -ra
```

Uso sin pytest (desde la raíz, con `backend` y raíz en PYTHONPATH):

```python
from experiments.optimization.loader import load_problem
from app.modules.optimization.domain.first_fit import FirstFitOptimizer
result = FirstFitOptimizer().optimize(load_problem("EXP-SMALL-001"))
```

La [evidencia](../../docs/evidence/sprint-02/TA-027/README.md) contiene fichas, matriz,
hashes y sanidad. No hay runner de benchmark, ranking ni implementación de TA-028/029.
Para nuevas revisiones experimentales, versionar cambios y actualizar hashes/evidencia;
no sobrescribir las instancias durante las ejecuciones.
