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
hashes y sanidad. TA-027 no incorpora ranking ni implementación de TA-028/029.
Para nuevas revisiones experimentales, versionar cambios y actualizar hashes/evidencia;
no sobrescribir las instancias durante las ejecuciones.

## Sonda de concurrencia de OPT-MULTIMOTOR-VISUAL (T00)

Autor: Fabricio Melendez Quezada. Revisor asignado: Andro Quispe.

Desde la raíz, con el Python del backend:

```text
python experiments/optimization/probe_concurrency.py
```

La sonda usa tres procesos `spawn`, una entrada JSON común y una barrera dentro
del primer hecho real de cada cálculo. Comprueba identidades, solapamiento,
igualdad con ejecución directa y ausencia de cambios en la entrada. Solo usa
datos sintéticos; no conecta a la base. Sus tiempos incluyen instrumentación y
no sirven para elegir el mejor motor. La suma de RSS máximos de workers no
equivale al pico agregado simultáneo ni certifica capacidad de producción.
La aplicación nunca importa esta sonda; no es un coordinador productivo.

Esta versión de la sonda necesita Linux con procfs para la medición agregada.
Añadir `--resource-cases` ejecuta también escenarios de
150 unidades, 50 unidades físicas de stock, 128 vértices y una rejilla de cuatro
millones de celdas. La sonda muestrea RSS del supervisor y los tres trabajadores
por PID, verifica que observó los cuatro y conserva tamaños JSON de entrada y
resultado. Se excluyen web, retención visual y el auxiliar `resource_tracker`;
las muestras pueden omitir picos y contar páginas compartidas varias veces.
La [evidencia de recursos](../../docs/evidence/sprint-02/OPT-MULTIMOTOR-VISUAL/t00-recursos.md)
explica los límites; los escenarios no certifican el triple peor caso.

`python experiments/optimization/probe_runner.py` ejercita el runner incorporado
a la aplicación con sus límites, IPC acotado y cierre supervisado, en los siete
escenarios. Comprueba fidelidad de los tres resultados y hechos de orden y
registra memoria/colas/paquetes. No levanta servidor web ni certifica el
presupuesto con retención visual completa. Véase la
[evidencia del coordinador](../../docs/evidence/sprint-02/OPT-MULTIMOTOR-VISUAL/t02-coordinador.md).
