# PLAN TA-044 - Capacidad, estres y concurrencia

Autor: Luis Anthony Ibanez Herrera. Revisor esperado: Andro Joseph Quispe Cesias.
Estado: en progreso; review formal pendiente.

## T01 - Datasets

Generar y validar los casos deterministas 10, 25, 50, 75, 100, 150 y 200
con `experiments/optimization/capacity_scenarios.py` y
`backend/tests/unit/optimization/test_capacity_scenarios.py`. Los casos usan
resolucion 1 mm, paso angular 5 grados, margen y separacion de 1 mm.

## T02 - Capacidad

Ejecutar `experiments/optimization/benchmark_capacity.py` para los seis metodos;
registrar colocaciones, estado, motivo de parada, tiempo, stock y metricas en
JSON y CSV. `tracemalloc` observa asignaciones Python, no RAM total.
Consultar `docs/evidence/sprint-02/TA-044/README.md` para la ejecucion registrada.

## T03 - Concurrencia

La sonda `probe_concurrency_capacity.py` mide igualdad de huellas y paralelismo
 del motor; no sustituye las pruebas del servicio. Ejecutar las pruebas API y de
integracion con PostgreSQL temporal en loopback para verificar admision, rechazo,
cancelacion, persistencia, inventario y aislamiento. Determinar el limite observado
solo despues de ejecutar y revisar esas pruebas.

## Cierre

Actualizar TASKS, SPEC, revision y evidencia solo con resultados comprobados.
La evidencia versionada es Markdown, JSON y CSV; no se afirma que exista un Word.
