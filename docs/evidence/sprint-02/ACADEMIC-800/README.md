# ACADEMIC-800 — Validación local del 08/11/2026

Base: `integration-02` en `1277c742de2dc347fab49060b74726c03e8f4341`.
[Especificación](../../../specs/SPEC-ACADEMIC-800-metodos-independientes.md).
Estado: propuesta para revisión; integración desplegada pendiente de validación.

## Qué cambió

M6 ya no termina con First Fit tras agotar su búsqueda. Devuelve la última
frontera nativa completa y conserva su causa de parada; un parcial no es elegible
para confirmar. El código de respaldo se elimina, junto con su interruptor.
Los resultados históricos que sí usaron respaldo conservan su lectura y etiqueta.

La política nueva BS-2 evalúa hasta doce sucesores por padre, conserva dos
estados y propone una primera posición factible por fuente/orientación.
Prioriza giros ortogonales y luego los demás giros configurados; elimina fuentes
vacías simétricas conservando la identidad física elegida. Puntúa cobertura,
área colocada, material usado y envolvente ocupada. Esta es una variante declarada:
puede producir otros cortes que la puntuación residual histórica. La reproducción
anterior usa `candidate_limit=None, positions_per_orientation=2`, sin respaldo.
Las pruebas de fidelidad histórica siguen comprobando sus cortes y métricas.

La admisión sube de 300 a 800 unidades físicas. Backend, consumidores v1/v2 y
estado visual aceptan 800 referencias de orden; 801 se rechaza. El máximo de
un evento de comparación pasa a 128 KiB para que el orden no se trunque.

## Carga y procedimiento

Se ejecutó cada adaptador productivo en un proceso nuevo, secuencialmente,
con 256 MiB de espacio virtual y checkpoint de 120 s. M6 conserva 32 MiB de
estado y hasta 110 s nativos. Entorno: Linux administrado, CPython 3.12.14;
la versión declarada del proyecto es 3.11.9 y requiere comprobación en CI.
Los tiempos son una medición local, sin estimación estadística ni garantía SLA.
Durante parte de la toma también corrieron las pruebas del proyecto.

Cada lote contiene dos grupos de vidrio de 6 mm, repartidos por igual, con
rectángulos de 120×80 mm, círculos de radio 40 mm y paralelogramos convexos
repetidos. Cada grupo dispone de dos planchas físicas de 2440×3300 mm.
Resolución de 1 mm, paso angular de 5°, margen y separación de 3 mm.
Se usan las mismas entradas por método, sin modificar base remota ni inventario.
`calculate_metrics` revalida cada colocación con `SheetLayout.place` antes de
contabilizarla: contorno, solapamiento y separación se verifican en el raster.

Comando, desde `backend`, con las dependencias del proyecto instaladas:

```bash
python -m scripts.benchmark_academic_800
# Un caso:
python -m scripts.benchmark_academic_800 --units 800 --method M6-BS
```

## Resultados observados

| Unidades | Método | Colocadas | Tiempo s | Pico RSS proceso MiB | Terminación |
|---:|---|---:|---:|---:|---|
| 600 | FF | 600 | 4.30 | 20.82 | COMPLETED |
| 600 | BF | 600 | 10.47 | 22.00 | COMPLETED |
| 600 | WF | 600 | 9.05 | 21.64 | COMPLETED |
| 600 | HF | 600 | 4.52 | 20.97 | COMPLETED |
| 600 | M5 | 600 | 49.63 | 22.02 | COMPLETED |
| 600 | M6-BS | 600 | 70.62 | 28.98 | COMPLETED |
| 700 | FF | 700 | 5.30 | 20.96 | COMPLETED |
| 700 | BF | 700 | 12.23 | 22.24 | COMPLETED |
| 700 | WF | 700 | 10.08 | 22.20 | COMPLETED |
| 700 | HF | 700 | 5.18 | 20.92 | COMPLETED |
| 700 | M5 | 700 | 63.91 | 22.13 | COMPLETED |
| 700 | M6-BS | 700 | 86.55 | 31.46 | COMPLETED |
| 800 | FF | 800 | 7.22 | 21.09 | COMPLETED |
| 800 | BF | 800 | 18.07 | 23.68 | COMPLETED |
| 800 | WF | 800 | 13.15 | 23.64 | COMPLETED |
| 800 | HF | 800 | 5.96 | 21.82 | COMPLETED |
| 800 | M5 | 800 | 81.58 | 23.79 | COMPLETED |
| 800 | M6-BS | 800 | 106.27 | 32.89 | COMPLETED |

Las 18 ejecuciones completaron y revalidaron 12 600 colocaciones en total.
Cada ejecución utilizó dos planchas. Los seis métodos empataron en área y
aprovechamiento: 24,126 % para 600, 28,168 % para 700 y 32,207 % para 800.
Este lote prueba volumen y validez; no demuestra superioridad de calidad entre
heurísticas ni cobertura de 800 geometrías grandes distintas.

M6 completó 600/700/800 niveles nativos, con fronteras máximas de dos estados,
10 388/12 108/13 868 expansiones y 12 786/14 906/17 066 sondeos.
Su cota máxima de estado para 800 fue 27 537 209 bytes, inferior a 32 MiB.
No hubo contadores de respaldo ni sustitución por otra ejecución. El tiempo de
800 deja poco margen respecto de sus 110 s nativos: un servidor más lento o la
observación/IPC pueden producir un parcial, que debe mantenerse explícito.

HF conserva su diseño híbrido existente: en estos lotes no aceptó bolsillos
(`accepted_pocket=0`) y retuvo sus candidatos de base (`fallback_used=600/700/800`).
Ese comportamiento se informa como HF; no es evidencia de mejora por rellenado
de huecos. No se ha convertido HF en una búsqueda pura diferente de su diseño.

## Pruebas y límites de esta evidencia

- Suite backend general: **2368 passed, 903 skipped**, sin fallos en las pruebas
  ejecutadas; los saltos requieren PostgreSQL local, ausente en este entorno.
  Se excluyeron de esa invocación las cuatro suites de recursos que el CI ejecuta
  en procesos separados, igual que en `.github/workflows/ci.yml`.
- Tras los últimos ajustes: **141 passed** en independencia M6, adaptador,
  aceptación y tamaño de eventos; **35 passed** en presupuesto de carga.
  Otra ejecución focalizada de memoria/independencia/límites pasó **41 pruebas**.
- Frontend: **215** pruebas unitarias y **606** de componentes aprobadas;
  `npm run lint` y `npm run build` aprobados. La compilación conserva su aviso
  de tamaño de bundle superior a 500 kB.
- Las pruebas nuevas de streaming envían realmente el evento de 800 referencias,
  mayor de 64 KiB y menor de 128 KiB, fragmentado en chunks, por ambos consumidores.
- `git diff --check` aprobado.
- Las suites aisladas de procesos **no aprobaron en este entorno**:
  `test_sequential_runner.py`: 7 passed / 19 failed;
  `test_comparison_runner.py`: 4 passed / 10 failed.
  Los fallos alcanzados están en el preflight del entorno, con
  `ValueError: Linux procfs required` / `RESOURCE_UNAVAILABLE`, antes de
  despachar los motores; el acceso `/proc/<pid>/statm` requerido no está disponible
  de forma útil. No se alteró ni se omitió esa protección para simular aprobación.
- No se ejecutó E2E de navegador ni persistencia PostgreSQL. Deben validarse
  en Linux con procfs y PostgreSQL antes de integrar/desplegar. El benchmark
  directo de adaptadores no certifica HTTP, IPC, observación o latencia del servidor.

Comando de la suite backend general:

```bash
python -m pytest tests \
  --ignore=tests/unit/optimization/test_comparison_runner.py \
  --ignore=tests/integration/optimization/test_comparison_calculation.py \
  --ignore=tests/integration/optimization/test_comparison_supervision_v2.py \
  --ignore=tests/unit/optimization/test_sequential_runner.py -q -ra
```

No se ejecutaron migraciones remotas, confirmaciones de cortes ni consumo de
stock. La propuesta no cambia la página publicada hasta su integración y despliegue.
