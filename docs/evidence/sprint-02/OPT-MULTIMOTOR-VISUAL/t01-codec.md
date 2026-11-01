# OPT-MULTIMOTOR-VISUAL — Codec de entrada y resultados

Autor: Fabricio Melendez Quezada.
Revisor asignado: Andro Quispe; revisión pendiente.
Fecha: 31/10/2026.
Estado: fundamento parcial de T01; no entrega de API ni interfaz.

## Cambio y contrato

Commit `2323e94dab70a0da69153e69a31380378366418a`,
`feat(optimization): versionar snapshots de los tres motores`.

El módulo `backend/app/modules/optimization/infrastructure/comparison_snapshot.py`
añade un transporte JSON desconectado para `spawn` y resultados con método
explícito. No modifica `run_snapshot.py` ni las rutas FF históricas.

| Formato | Contenido e invariantes |
|---|---|
| Entrada `input_version: 1` | `problem`: pedidos, configuración, unidades originales, grupos y stock con su orden; decimales como strings y geometrías canónicas |
| Resultado `snapshot_version: 2` | Sobre con `method: FF/BF/WF` y resultado; reconstruye la clase del motor, sin calcular nuevamente |
| Resultado histórico V1 | Se interpreta únicamente como FF; conserva la lectura de metadatos históricos y rechaza atribuirlo a BF/WF |
| Hash de entrada | SHA-256 del JSON canónico completo; también cambia al variar cantidades, configuración o ranking del stock |

Los objetos reconstruidos son independientes y conservan la inmutabilidad del
dominio. Un método esperado incompatible con el sobre se rechaza. También se
rechazan versiones desconocidas o booleanas, JSON no finito y sobres V2 extraños.
Los límites del documento serializado son 4 MiB por entrada y 8 MiB por
resultado. Estos límites no equivalen a un presupuesto de memoria residente ni
constituyen todavía validación de admisión agregada.

## Verificación

Desde `backend`, después de restablecer el entorno de ejecución:

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m pytest tests/unit/optimization/test_comparison_snapshot.py tests/unit/optimization/test_first_fit.py tests/unit/optimization/test_best_fit.py tests/unit/optimization/test_worst_fit.py -q -ra -p no:cacheprovider
```

Resultado: **100 passed in 0.62s**. Las 24 pruebas nuevas incluyen round-trip
de resultados completos y parciales FF/BF/WF, geometrías, métricas, tiempos,
remanentes, huella sensible a cambios, independencia de entrada, rechazo de
métodos cruzados y lectura FF V1. La decodificación se verifica con los tres
optimizadores bloqueados para detectar un recálculo accidental.

Tras ampliar la sonda de recursos se repitió la misma selección más
`tests/unit/optimization/test_experimental_cases.py`: **123 passed in 1.80s**.

## Alcance pendiente

El codec aún no está conectado a la persistencia del agregado comparativo ni a
una API nueva. T01 conserva pendientes el snapshot de solicitud enriquecido,
las identidades/versiones, la selección y la migración. T00 sigue abierto por
el presupuesto productivo y los contratos; T02–T07 no se declaran entregadas.
