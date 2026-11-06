# Comparador v2: rendimiento (2026-11-06)

Rama `fix/S2-rendimiento-comparador`, base `ec46a7a` de `recovery/sprint-02`.
Datos sintéticos autorizados; no es una reproducción exacta del pedido #69.

## Diagnóstico y cambio

Los seis procesos son secuenciales y comparten **180 s globales**. Cada proceso
tiene además 30 s de arranque y 120 s de cálculo; el plazo global incluye
preparación, IPC, espera del consumidor y persistencia entre motores. Las fechas
de inicio se crean juntas: los tiempos de finalización son acumulativos, no CPU.
Tras agotarse el plazo, los motores aún en cola reciben `GLOBAL_TIME_LIMIT` sin arrancar
(`runtime_dispatched=0`, `runtime_engine_started=0`). Persistir esos fallos y cerrar
la supervisión puede terminar después del segundo 180. Es el contrato vigente.
No se dispone de una traza histórica para atribuir tiempos internos al trabajo #20.

El cuello demostrado está en `SheetLayout.first_position`: restricciones de filas
repetidas sobre las mismas franjas libres, especialmente con círculos y polígonos.
La instrumentación de 46 unidades atribuye 29,923/33,827 s de FF y 55,567/60,050 s
de HF a esa búsqueda. Las máscaras ya se comparten por geometría dentro de cada
motor; no se encontró motivo para compartir cachés entre procesos.

La corrección conserva el rechazo rápido de la primera fila, intersecta primero
las restricciones más densas y omite máscaras contenidas en la unión ya comprobada
contra un mismo patrón de fila libre. La intersección es conmutativa: conserva
exactamente el primer origen por fila/columna. La unión es local a cada fila
candidata y se descarta al cambiar el patrón libre. No se agregan cachés globales,
heurísticas de colocación,
paralelismo ni aumentos de presupuestos. Márgenes, separación, rasterización,
validación, checkpoints, supervisión, persistencia y recuperación siguen vigentes.
El dominio exige coincidencia de material y espesor en cada grupo.

## Mediciones

WSL Ubuntu, Python 3.11.9; PostgreSQL 18 temporal de loopback migrado a `head`.
Mismo checkout, dependencias, datos, observación visual activa y límites por defecto;
sin otras suites simultáneas. Una corrida completa por tamaño antes/después,
sin perfilador. Son tiempos de pared; no estimaciones de CPU ni medianas.

Dos materiales sintéticos (IDs 7/9), ambos de 6 mm; cuatro planchas de 2140×3300 mm
por material. Rejilla de 1 mm, margen/separación de 3 mm y ángulos de 5°.
Por grupo se alternan rectángulos de 600×800 mm, círculos de radio 260 mm y el
pentágono convexo `(0,0),(500,0),(620,400),(250,700),(0,400)` (317000 mm²).
Las 46 unidades se reparten 23/23; las cargas de 6 y 18 mantienen el mismo stock.

| Unidades | Antes (s) | Después (s) |
|---|---:|---:|
| 6 | 14,136 | 16,011 |
| 18 | 24,120 | 22,336 |
| 46 | 171,681 | 64,389 |

La carga grande mejora **62,5 %**; la pequeña no demuestra mejora.

| Motor, 46 unidades | Pared externa antes/después (s) | Búsqueda antes/después (s) |
|---|---:|---:|
| FF | 33,827 / 6,046 | 29,923 / 2,892 |
| BF | 33,324 / 6,953 | 28,831 / 2,915 |
| WF | 7,428 / 6,120 | 2,757 / 1,708 |
| HF | 60,050 / 9,592 | 55,567 / 5,706 |
| M5 | 27,535 / 26,835 | 1,146 / 1,352 |
| M6-BS | 0,076 / 0,079 | No inicia búsqueda |

Arranque por motor: 1,13–1,44 s antes / 1,15–1,22 s después. Preparación de bases:
0,027–0,038 s después; rasterización total, incluidas orientaciones perezosas:
0,021–0,213 s; métricas: 1,47–2,22 s. Las transacciones suman 8,818 / 6,970 s.
Estos componentes se solapan: no deben sumarse a la pared externa.
RSS agregado máximo (incluida reserva): 226,48 / 226,27 MiB; límites sin cambios.

La repetición con instrumentación de persistencia dio 66,604 s: aceptación 0,458 s,
transacciones 7,432 s (referencias visuales 4,967 s; resultados y commit 0,539 s).
Proyectar y serializar el resumen y seis respuestas (157132 bytes) tomó 0,0105 s;
codificar snapshots, 0,0173 s. Esto mide entrega local hasta bytes, no red ni
latencia de un navegador. No se demostró un cuello en rasterización o serialización.

Los snapshots completos coinciden en los 18 resultados salvo `computation_time_ms`:
contornos, posiciones, giros, métricas y diagnósticos iguales. FF/BF/WF/HF/M5 colocan
las 46 unidades. M6-BS retorna parcial vacío `STATE_MEMORY_LIMIT`: la cota previa
de ocho planchas a 1 mm supera sus 32 MiB. **No completan los seis motores**.
Stock intacto y cero movimientos de inventario en todas las corridas.

## Validación y límites

Backend completo: **3237 aprobadas**, cero omitidas: principal 3163 y suites
aisladas de cálculo 8, supervisión v2 26, runner secuencial 26 y runner v1 14.
Se ejecutó la separación de procesos del CI con PostgreSQL obligatorio y temporal;
incluye las regresiones TA-045, TA-047 y TA-049, límites, checkpoints, motores sin
despachar, resultados parciales y cierre verificado. Una advertencia previa de
deprecación Starlette/httpx en la suite principal.
Frontend: **213 unitarias y 589 de componentes (57 archivos) aprobadas**, cero
omitidas; lint y build aprobados. Código de frontend y dependencias sin cambios.
Gate conjunto **TA-040 PASS: 146/146**, sin omisiones, escritorio y móvil;
B02 2 y fase restante 144, con servidores y clústeres nuevos por fase.
La regresión nueva contrasta 1920 búsquedas con el validador exhaustivo, además de
casos específicos con filas vacías, máscaras desconectadas y desempates.
No se versionan salidas de pruebas. Reproducción desde `backend/`, con dependencias
y PostgreSQL locales: `NEWGLASS_REQUIRE_POSTGRES=1 NEWGLASS_TEST_PG_BIN=<binarios>`
y `python -m scripts.benchmark_comparison 6 18 46`. El script crea y detiene su
propio clúster; emite mediciones y snapshots sintéticos por stdout.

El resultado depende de la geometría, resolución y stock. M5 conserva otros costos
de búsqueda; M6 conserva límites nativos de memoria/tiempo. No se garantiza que
el pedido real #69 complete seis resultados ni se midió latencia de Supabase.
No se modificó Supabase, el pedido real ni inventario externo; sin push ni merge.

## Finalización S2: M6-01 y M6-02

Base `2402142`; rama `feat/S2-finalizacion-comparador`. La cota fija de M6 se
sustituye por el grafo compartido por identidad y reservas conservadoras de
construcción, búsqueda, puntuación, ordenamiento y contabilidad. Se conservan
32 MiB, BS-2, 12 hijos, 30 s, 60000 expansiones y 1000000 sondeos. La búsqueda
inversa usa bits, pero carga también los sondeos lógicos descartados, manteniendo
el mismo corte por recursos. Los scores reutilizados pertenecen al mismo layout
inmutable: no se deduplican estados ni se cambia el desempate.

`python -B -m scripts.benchmark_beam_viability` reproduce siete casos por seis
métodos en procesos nuevos de 256 MiB de espacio virtual. JSON por stdout incluye
pared con métricas, cobertura, fuentes, aprovechamiento, merma, origen, causa,
contadores y RSS del proceso (incluye intérprete/caché; no es memoria de estados).
WSL/Python 3.11.9, una corrida por caso, sin suites simultáneas. Estas mediciones
directas no ejercitan el plazo compartido de 180 s del comparador.

| Caso M6 | Colocadas | Pared con métricas (s) | Causa | Reserva pico (MiB) |
|---|---:|---:|---|---:|
| Original, 6 unidades / ocho planchas | 0/6 | 30,003 | TIME_LIMIT | 25,173 |
| Original, 18 unidades / ocho planchas | 0/18 | 30,003 | TIME_LIMIT | 25,213 |
| Original, 46 unidades / ocho planchas | 0/46 | 30,003 | TIME_LIMIT | 25,306 |
| Seis mixtas, una plancha 1000×1000 | 5/6 | 22,975 | GEOMETRY_PROBE_LIMIT | 4,503 |
| 18 círculos r=40, una plancha 500×500 | 18/18 | 0,956 | COMPLETED | 1,245 |
| Seis círculos r=80, cuatro retazos 500×500 y plancha 1000×1000 | 6/6 | 1,618 | COMPLETED | 3,086 |
| Seis círculos r=80, grupos de 6/8 mm y dos planchas 1000×1000 | 6/6 | 0,589 | COMPLETED | 3,039 |

Las mixtas pequeñas alternan rectángulo 200×300, círculo r=100 y pentágono
`(0,0),(125,0),(155,100),(62.5,175),(0,100)`. Margen/separación 3 mm, rejilla 1 mm,
giros 5°. Los otros cinco motores completaron los siete casos (35/35); M6 completó
3/7. En las cargas originales M6 no completa el primer nivel: la frontera
anterior está vacía y se devuelve así, sin inventar placements de un nivel
interrumpido. La admisión de memoria ya no es la causa; puntuar alternativas
grandes sigue siendo costoso. No se garantiza completar pedidos comerciales.

Frente a la auditoría anterior, M6 pasó de 13,408 a 0,956 s en 18 círculos pequeños
y de 8,012 a 1,618 s en retazos. Son corridas únicas: no medianas ni garantías.
No se equipara esta matriz sintética con el pedido real #69.

Comparador productivo con observación, persistencia y PostgreSQL 18 temporal:
46 unidades en 101,557 s, RSS agregado máximo 245,08 MiB, sin causa global y con
todos los workers detenidos. FF/BF/WF/HF/M5 colocan 46/46 y sus snapshots completos
coinciden con la medición previa salvo `computation_time_ms`. M6 devuelve
ENGINE/TIME_LIMIT, 0/46 y reserva pico 25,323 MiB. Se despacharon e iniciaron los
seis motores; solo cinco completaron. Stock intacto y cero movimientos.

### Comprobación manual pendiente del pedido #69

En la versión final aprobada y un entorno autorizado: anotar commit, revisión
Alembic y configuración; consultar las piezas/medidas reales de #69 y el stock
por material/espesor antes de iniciar. Crear una comparación desde la UI y anotar
su número. Esperar el cierre; registrar por método cobertura, fuentes, métricas
y causa de terminación. Reabrir desde historial y actualizar sin recalcular.
Comparar 2D/3D y fuentes propuestas contra el inventario inicial: la simulación
no debe consumir stock. No confirmar sobre inventario real durante esta prueba.
Una comprobación del consumo requiere autorización independiente y un pedido de
prueba controlado. Hasta ejecutar este protocolo, #69 continúa sin verificar.
