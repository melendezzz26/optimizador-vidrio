# PLAN-TA-QA-002 — Plan de Ejecución de Rendimiento y Carga

## 1. Objetivo y Estrategia

El presente plan establece la estrategia técnica y metodológica para llevar a cabo la medición de rendimiento, capacidad y consumo de recursos de los seis motores de optimización (`FF`, `BF`, `WF`, `HF`, `M5`, `M6-BS`) requerida en la tarea `TA-QA-002`.

La estrategia se basa en:
1. **Reproducibilidad estricta:** Un único script parametrizable (`backend/scripts/benchmark_qa_002.py`) capaz de ser ejecutado por cualquier miembro del equipo o revisor, con salidas estandarizadas en consola y en formato JSON.
2. **Representatividad estadística:** Medición por iteraciones ($N \ge 3$) con cálculo de percentiles $\text{p50}$ (mediana) y $\text{p95}$, superando la debilidad de las mediciones de una sola corrida realizadas previamente.
3. **Aislamiento de procesos:** Lanzamiento de cada motor en un subproceso hijo independiente mediante `multiprocessing.get_context('spawn')`, garantizando que la memoria y el recolector de basura de Python no se acumulen entre iteraciones.

---

## 2. Arquitectura de Aislamiento y Muestreo

```text
[ Proceso Padre (Supervisor QA) ]
        │
        ├── Inicia subproceso hijo con multiprocessing.spawn
        │       │
        │       ├── Proceso Hijo (Worker Motor):
        │       │     1. Prepara problema geométrico sintético canónico.
        │       │     2. Inicia contador de tiempo time.monotonic().
        │       │     3. Ejecuta EngineExecutionAdapter(method).execute(...).
        │       │     4. Valida checkpoint de tiempo (120 s).
        │       │     5. Emite resultado por Pipe.
        │       │
        ├── Hilo Monitor (psutil):
        │       └── Sondea periódicamente process.memory_info().rss cada 50 ms.
        │           Registra el valor pico alcanzado por el worker.
        │
        └── Recolecta métricas:
                └── Almacena tiempos, pico RSS, piezas colocadas, planchas y motivo.
```

### Cálculo de Percentiles
Para un conjunto ordenado de $N$ tiempos $T = [t_1, t_2, \dots, t_N]$:
* **p50 (Mediana):** Valor central (o promedio de los dos centrales si $N$ es par).
* **p95:** Calculado mediante interpolación lineal de percentiles (`numpy.percentile(T, 95)` o equivalente nativo).

---

## 3. Gestión de Riesgos y Mitigación

| Riesgo Técnico | Impacto | Mitigación |
|---|---|---|
| **Dispersión por fluctuaciones de CPU en Windows** | Variación no determinista de tiempos de reloj. | Mínimo de 3 iteraciones; ejecución en máquina sin procesos pesados de fondo; cálculo de mediana (p50) como indicador robusto. |
| **Bloqueo por cálculo infinito en motores con problemas** | El proceso de prueba se cuelga indefinidamente. | Checkpoint interno a los 120 s en el motor y timeout de terminación forzada en el supervisor a los 150 s (`process.terminate()`). |
| **Contaminación de memoria entre iteraciones** | El RSS de la corrida $k+1$ hereda memoria de la corrida $k$. | Uso exclusivo del modelo `spawn` de multiprocesamiento: cada iteración muere y libera su memoria al SO. |
| **Sobregeneración de expectativas sobre capacidad (800 u)** | Declarar que el sistema soporta 800 piezas en producción cuando solo lo hace en condiciones académicas reducidas. | Análisis explícito de la frontera de fallo: documentar que con piezas estándar a 5° el límite práctico es 200 piezas y en 300 piezas se agotan los 120 s. |

---

## 4. Fases de Ejecución

1. **Fase 1 — Creación del Script de Benchmark (`T02`):** Desarrollar `backend/scripts/benchmark_qa_002.py` con soporte para iteraciones, cálculo de p50/p95 y muestreo de memoria RSS con `psutil`.
2. **Fase 2 — Ejecución del Lote Base Requerido (`T03`):** Correr las cargas de 10, 25, 50, 100, 150 y 200 unidades, registrando tiempos y memoria de los 6 motores.
3. **Fase 3 — Análisis de Límites en Cargas Mayores (`T04`):** Evaluar 300 unidades comerciales y contrastar contra el benchmark académico de 800 unidades pequeñas.
4. **Fase 4 — Tabulación Comparativa y Correlación con Heroku (`T05`):** Construir matrices de comparación contra los números de Melendez y contrastar con los eventos H27/R12 de Heroku.
5. **Fase 5 — Documentación de Evidencia y Cierre SDD (`T06`):** Redacción de `docs/evidence/sprint-02/TA-QA-002/README.md`, generación del informe Word/Notion y paso de la SPEC a `Verified`.
