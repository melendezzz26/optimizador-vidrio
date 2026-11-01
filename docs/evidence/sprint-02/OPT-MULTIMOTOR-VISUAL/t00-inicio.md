# OPT-MULTIMOTOR-VISUAL — Inicio de T00

Autor: Fabricio Melendez Quezada.
Revisor asignado: Andro Quispe; revisión cruzada pendiente.
Fecha: 31/10/2026 (America/Lima).
Estado: evidencia parcial de T00; no cierre funcional de la SPEC.

## Aprobación y trazabilidad

Fabricio Melendez Quezada aprobó SPEC y PLAN, corrigió autoría/revisor y autorizó
el desarrollo exclusivamente en `feature/optimization-multimotor-visual`.
La SPEC pasó a Reviewed y el PLAN a Approved en `c44184e`. Esto no atribuye
una revisión ya realizada a Andro Quispe ni declara funcionalidad verificada.

## Sonda ejecutada

Código reproducible: `experiments/optimization/probe_concurrency.py`, commit
`eb40a2134a224ac2cb9571928b9e117be9184e4a`. Ejecución desde la raíz:

```text
PYTHONDONTWRITEBYTECODE=1 backend/.venv/bin/python -B experiments/optimization/probe_concurrency.py
```

Entorno: Linux, Python 3.11.9, cgroup con 8 GiB de límite de memoria y cuota de
CPU equivalente a dos núcleos. Es el entorno de trabajo, no una observación del
despliegue remoto. La sonda usa únicamente datos sintéticos congelados y no DB.

| Caso | Unidades | Solapamiento de llamadas (ms) | Suma de máximos RSS de workers (MiB) | Igualdad con ejecución directa |
|---|---:|---:|---:|---|
| EXP-SMALL-001 | 3 | 10.135 | 59.45 | Sí |
| EXP-MEDIUM-001 | 9 | 15.935 | 60.95 | Sí |
| EXP-COMPLEX-001 | 24 | 113.981 | 61.70 | Sí |

En cada caso se comprobó:

- Tres PID distintos y métodos FF/BF/WF identificados.
- Mismo hash de entrada en padre y trabajadores, transportada como JSON con spawn.
- Solapamiento de las tres llamadas, mediante una barrera instrumentada dentro
  del primer hecho real emitido por cada optimizador.
- Resultados, métricas y retazos residuales iguales a la ejecución directa de
  cada motor, excluyendo relojes e identificadores del sistema operativo.
- Conservación del hash de la entrada y cierre de los trabajadores al terminar.

La salida estructurada está en [t00-concurrency.json](t00-concurrency.json).

## Límites de esta evidencia

La barrera participa del tiempo transcurrido: estos tiempos no sirven para
ranking ni para comparar rendimiento de los motores. La suma de máximos RSS no
es una medición del pico agregado simultáneo. Los casos congelados son pequeños;
no se certifican con ellos el peor caso, la capacidad de producción ni umbrales
agregados para tres cachés/layouts.

La sonda no es el coordinador productivo, no se importa desde la aplicación y
no implementa API, selección, persistencia, confirmación ni interfaz. Esta
comprobación inicia T00 y aporta viabilidad de spawn y fidelidad de entrada/salida;
los presupuestos agregados y contratos quedan pendientes antes de cerrar T00.
No se declara ningún CA del producto como PASS únicamente por esta sonda.

## Regresión de entradas congeladas

Comando desde la raíz:

```text
PYTHONDONTWRITEBYTECODE=1 backend/.venv/bin/python -B -m pytest backend/tests/unit/optimization/test_experimental_cases.py -q -ra -p no:cacheprovider
```

Resultado: **23 passed in 1.26s**. Además se comprobaron sintaxis de la sonda,
enlaces de SPEC/PLAN y ausencia de errores de whitespace en los cambios.
