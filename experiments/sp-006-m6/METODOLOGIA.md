# SP-006 — Método y equivalencia experimental

Versión algorítmica: **SP006-BS-v1**. Alcance: investigar M6; decisión humana
pendiente. No se implementan TA-053 T01/T02, endpoints, UI, coordinador,
persistencia ni consumo/reserva de inventario.

## 1. Auditoría de arquitectura y fuentes

Base: integración remota `f9cfd4f2644455d616699518948c6660006bdae8`, verificada el
02/11/2026. NewGlass es un monolito modular. `Optimization` separa dominio puro,
aplicación, infraestructura y presentación; la aplicación no importa experiments.

Flujo relevante: `prepare_persisted_problem` valida piezas con Orders →
`prepare_problem` expande cantidades y ordena → `with_compatible_stock` captura
stock compatible → `packing.pack` prepara raster/orientaciones → selector →
`SheetLayout.place` produce estado inmutable → `OptimizationResult` →
`calculate_metrics` revalida y calcula. FF/BF/WF comparten ese recorrido;
FF termina al primer candidato, BF/WF comparan capacidad raster posterior.

Fuentes revisadas (rutas relativas a la raíz del repositorio):

- `CONTRIBUTING.md`, `docs/adr/ADR-001-seleccion-arquitectura.md` como marco arquitectónico.
- `docs/specs/SPEC-SP-002-reglas-comunes-heuristicas.md` y su PLAN;
  `docs/evidence/sprint-02/SP-002/README.md` (matriz de reglas comunes).
- SPEC/PLAN de TA-027, TA-020 y TA-016; SPEC de TA-021 y OPT-MULTIMOTOR-VISUAL.
- `backend/app/modules/optimization/{domain,application,infrastructure}`:
  contratos, preparación, stock, packing, máscaras, rotación, placement y métricas.
- `backend/app/modules/optimization/infrastructure/stock_adapter.py`:
  selección y orden reales de disponibilidad. No se copia ese adaptador.
- `experiments/optimization/README.md`, `loader.py`, los tres JSON y
  `docs/evidence/sprint-02/TA-027/{README.md,sanity.json}` como procedencia.

El snapshot portable reproduce 22 archivos originales listados con hashes en
`snapshot-manifest.json`. Los `__init__.py` son vacíos generados; no se copian
imports de infraestructura. Los imports del código de cálculo usan solo stdlib.
No se llama a router, configuración, SQLAlchemy, Supabase, inventario o red.
Se conserva incluso el whitespace original de `raster_mask.py:98`; una excepción
de atributo Git limitada a ese archivo permite revisar el diff sin alterar su hash.

## 2. Reglas exactas y contenido de las entradas

| Regla | Fuente / aplicación experimental |
|---|---|
| Geometrías | RECTANGULO, CIRCUNFERENCIA y POLIGONO_CONVEXO; plancha rectangular, retazo de cualquiera de las tres formas |
| Preparación | Grupos ordenados por (tipo de vidrio, espesor); unidades por área DESC, dimensión mayor de bbox DESC, pedido/pieza/índice ASC |
| Unidades | mm, mm², grados; resolución 1 mm y rotación habilitada en los tres JSON |
| Rotaciones | 0,5,…,355°; contorno normalizado a bbox local, coordenadas a seis decimales; cuartos de vuelta exactos; dedup por máscara completa conservando primer ángulo; círculo solo 0° |
| Rasterización | Pieza conservadora, material interior; se usan los bits reales de círculo/polígono, no su bbox como criterio de aceptación |
| Margen / separación | SMALL 0/0 mm, MEDIUM y COMPLEX 1/1 mm. Ceil exacto de distancia/resolución; erosión de material y dilatación cuadrada de ocupación. No es una nueva distancia euclídea continua |
| Compatibilidad | Igualdad exacta tipo de vidrio/espesor; grupos independientes |
| Stock disponible | En producción: retazos activos y planchas activas con cantidad >0. En TA-027: candidatos congelados explícitos, sin campo estado/fecha; todos se consideran disponibles como define el loader original |
| Orden de fuentes | Producción ordena fecha DESC, ID DESC, índice físico ASC dentro de nivel. TA-027 conserva orden del JSON dentro de nivel y expande cantidad a índices 1..N; no inventa fechas |
| Cantidades físicas | SMALL 1 retazo+1 plancha; MEDIUM 2+2; COMPLEX 3+4. Cada retazo es una unidad física; cada fuente admite múltiples placements hasta agotar espacio |
| Prioridad | Para la unidad y estado actuales: RETAZO compatible y geométricamente factible antes de PLANCHA. El área o bbox suficiente no demuestra factibilidad |
| Rechazo | NO_FIT se demuestra recorriendo fuentes/orientaciones; se sigue con la siguiente unidad. Fallo técnico/límite se identifica por separado |
| Inmutabilidad | Contratos congelados, geometría profundamente inmutable, layouts nuevos por placement, caché local y proceso nuevo por corrida |

SMALL: una definición de cuadrado 2×2, cantidad 3. MEDIUM: tres definiciones,
nueve unidades y círculos/rectángulos. COMPLEX: seis definiciones, 24 unidades,
dos materiales y polígonos convexos, incluyendo retazo irregular. Las rejillas
máximas son 22×16, deliberadamente pequeñas para CI. Se conserva todo el
contenido original, no solo esos conteos.

Hashes oficiales (bytes Git LF; las copias mantienen esos bytes):

| Fixture | SHA-256 |
|---|---|
| EXP-SMALL-001 | `8983a8291a272938650bbc0a5c0fb0a5affc33bef5a61ee9afc73a75caa583f5` |
| EXP-MEDIUM-001 | `eb50a3beaa2312fc94e4cd879b8961401b119f6370c08a5357680bb2b76535d9` |
| EXP-COMPLEX-001 | `c844a23d849a8f0f1903a827bb7d2f1b6782a386610dda14c2789520a5670478` |

## 3. Algoritmo reproducible de M6

Referencia normativa ejecutable: `sp006/beam.py`, incluidas SearchLimits y Node.score.
No cambia orden de piezas ni llama a FF/BF/WF. El contrato de resultado experimental
se identifica como M6-BS y el informe conserva BS-2/BS-3/BS-4 explícitamente.

**Nodo.** Tupla inmutable de layouts en el orden global estable de fuentes físicas,
tupla de placements, traza y número de unidades procesadas. La raíz contiene
layouts vacíos. Los contornos y máscaras inmutables se comparten solo dentro
de la corrida; no se comparten cachés entre métodos ni repeticiones.

**Etapa.** Se considera una unidad en el mismo orden común del backend. Se examina
exhaustivamente la factibilidad de todas las fuentes del nivel RETAZO mediante
las orientaciones comunes y `first_position`. Si hay alguna factible, se descarta
el nivel PLANCHA. Solo si todos los retazos fallan se examinan las planchas.
Un presupuesto interrumpido durante esa certificación abandona el nivel; nunca
habilita planchas por no haber alcanzado a revisar un retazo.

**Ramas.** Por cada fuente factible del nivel permitido y cada orientación distinta
se obtiene la primera posición válida por fila/columna. Se obtiene también la
última válida recorriendo filas y columnas en orden inverso con `layout.check`.
Si ambas coinciden se genera una sola. Cada rama añade exactamente un placement
mediante `layout.place`. Se exploran así decisiones espaciales, angulares y de
fuente propias; se podan las posiciones interiores intermedias. No se limitan
los giros a 0/90° ni se cambia el paso de 5°. Si no hay fuente factible se genera
un hijo NO_FIT sin placement. No hay rama de omisión voluntaria cuando cabe.

**Puntuación a minimizar lexicográficamente**, para profundidad d y placements P:

```text
(d − |P|,
 −sum(area nominal de piezas colocadas),
 cantidad de planchas físicas usadas,
 sum(area nominal de fuentes físicas usadas),
 −sum(area en celdas del máximo rectángulo libre de cada fuente usada),
 sum(area en celdas de la envolvente de ocupación de cada fuente usada),
 traza completa)
```

Las áreas nominales usan Decimal. Los dos términos raster usan celdas, idénticas
entre métodos de cada caso. El máximo rectángulo libre considera `usable & ~blocked`
y sirve de guía; la métrica final usa sus mínimos originales y mm². La envolvente
se calcula sobre bits ocupados, no sobre el contorno continuo. La traza de un
placement es `(0, rango fuente, rango orientación deduplicada, fila, columna)`;
NO_FIT usa `(1,-1,-1,-1,-1)`. Comparación natural de tuplas; empate exacto conserva
el orden estable de generación. No hay pesos, random ni un score de los baselines.

**Poda y cierre.** Se generan hijos uno a uno conservando los 12 mejores por padre,
luego los k mejores globales de ese nivel. No se deduplican nodos ni se hacen
rollouts con otros métodos. La frontera anterior se conserva hasta terminar
todos los padres de la etapa. Si se interrumpe, se descarta ese nivel incompleto
y se devuelve el mejor nodo de la frontera anterior. Tras completar todas las
unidades se devuelve el menor score de la frontera final. Si la preparación
se interrumpe antes de existir frontera, el worker informa LIMIT sin layout.

Esta es una búsqueda heurística con orden fijo y poda agresiva; no prueba
optimalidad. Un k mayor puede conservar ramas diferentes, sin garantía de mejorar.

## 4. Límites y medición

| Límite | Valor inicial y significado |
|---|---|
| Ancho k | 2, 3, 4; no se ajustó tras el preliminar, que terminó holgadamente |
| Hijos retenidos por padre | 12; se ordenan incrementalmente, sin acumular todos los sucesores |
| Posiciones por orientación | Primera y última; 2 máximo, deduplicadas si coinciden |
| Placements generados | 60.000; cuenta antes de podar. Los hijos NO_FIT no suman placements |
| Consultas geométricas | 1.000.000: cada llamada a first_position o check de posición alternativa. No cuenta operaciones internas del motor |
| Estados | Cota conservadora de 32 MiB antes de asignarlos; no es memoria RSS medida |
| Caché raster | 64 MiB del motor original; se mantienen también límites originales de geometría y precisión |
| Tiempo de cálculo | 30 s cooperativos por método; el supervisor mata el proceso después de 60 s totales |
| Memoria del proceso | Supervisor por RSS muestreada, límite 256 MiB, intervalo 10 ms |

La cota de estados suma por nodo `2048 + unidades*1024` más cuatro filas-bit por
fuente según `rows * (40 + 4*ceil(columns/30)) * 4`, y multiplica por
`3*k + children_per_parent + 3`. Sobreestima compartición de layouts; no pretende
reemplazar medición del heap ni limitar exactamente cada asignación transitoria.
La caché mantiene su presupuesto separado. El supervisor acota también memoria
total observada; un pico más breve que el intervalo puede no detectarse.

Cada cálculo corre secuencialmente en un intérprete nuevo. El tiempo medido
incluye build_problem, preparación raster, búsqueda y calculate_metrics;
excluye arranque, auditoría, figuras e instalación. La RSS incluye todo el
proceso observado, incluso arranque y auditoría. Se reporta el máximo muestreado,
no el high-water mark del sistema ni el incremento atribuible solo al algoritmo.
Mismas condiciones de instrumentación para FF/BF/WF y M6; orden inverso en la
segunda repetición. No reproduce la concurrencia del coordinador productivo.

Un límite de búsqueda puede devolver prefijo válido con `status=LIMIT`;
`pending_units` son unidades sin explorar y `no_fit_units` las imposibles en
el estado procesado. Si el supervisor mata un proceso no hay layout ni métricas.
LIMIT y ERROR se excluyen de las diferencias, no se convierten en ceros.

## 5. Métricas vigentes

`calculate_metrics` se copia sin cambios. Re-rasteriza a 0° el contorno ya
orientado, coloca de nuevo con margen/separación y rechaza geometría inconsistente.

- `material_area_mm2`: suma del área nominal de cada fuente física usada una vez.
  No suma stock sin utilizar ni solo superficie usable tras margen.
- `placed_piece_area_mm2`: suma del área nominal persistida de cada unidad colocada.
  El loader obtiene áreas con GeometryValidator y HALF_UP a 0,01 mm².
- `utilization_pct`: piezas/material ×100, HALF_UP a 0,001 puntos porcentuales.
- `recoverable_remnant_mm2`: como máximo un rectángulo raster libre por fuente usada,
  con ancho y alto mínimos 1 mm en estos fixtures. Empates: área DESC, fila ASC,
  columna ASC, ancho DESC, alto DESC. No suma todos los huecos libres.
- `waste_mm2`: material − piezas − recuperable; no se interpreta como `100−utilización`.
- `new_sheets_used`: fuentes físicas PLANCHA usadas. Retazos usados se cuentan
  adicionalmente desde materials_used. No se genera inventario con los residuales.
- Cero colocaciones: métricas ausentes; no hay denominador R4. Se conservan cantidades.

JSON conserva todos los placements, fuentes, giros, residuos, auditorías y metadatos.
CSV conserva cantidades, áreas, tiempos, RSS, validez y determinismo. Diferencias:
BS menos cada FF/BF/WF por mediana; porcentaje en puntos porcentuales. No hay ranking.

## 6. Equivalencia: qué se demuestra y qué no

| Nivel | Comprobación / límite |
|---|---|
| Datos | 3 JSON y loader originales byte a byte; hashes oficiales; mismas cantidades/reglas/stock y reconstrucción inmutable |
| Algoritmos base | FF/BF/WF originales, misma preparación y decisiones. Pruebas en procesos con imports originales versus portables para los nueve pares: placements y métricas idénticos |
| Geometría | Código original de máscaras, rasterización, rotación, layouts y métricas. Control manual SMALL; controles negativos de margen, separación, superposición, giro y prioridad |
| M6 | Amplía sucesores y cambia selección; reutiliza la misma aceptación geométrica. No debe producir el mismo layout que FF/BF/WF |
| Inventario | Snapshot sintético: no se comprueba ni reproduce una consulta en vivo. Se omiten por diseño estado/fechas que los fixtures no contienen |
| Recursos | Entorno CPU independiente, ejecución secuencial y auditoría adicional. No equivalencia de tiempos, memoria, admisión o concurrencia productivos |
| Evolución | La equivalencia se acota al commit congelado y entradas probadas; futuras versiones del motor requieren renovar snapshot y evidencia |

La auditoría independiente recorre el prefijo en orden, comprueba retazos antes
de cada plancha, valida cada NO_FIT, ángulos/contornos, alineación de rejilla,
stock contractual y check/place común. Geometría válida no demuestra una secuencia
de cortes guillotina: esa restricción no está en este contrato ni se incorpora aquí.

La igualdad original/portable se verificó en Windows/Python 3.11.9. No se probó
igualdad bit a bit entre Windows y Linux/Colab; el notebook repetirá los controles
de determinismo dentro del entorno donde se ejecute. Los metadatos permiten
identificar versiones y comparar ambas ejecuciones sin mezclar sus tiempos.

No existe sustitución raster ni aproximación oculta de FF/BF/WF. Eso permite una
comparación funcional fiel al dominio congelado, pero el estudio se mantiene
**exploratorio SP-006**, fuera de un benchmark oficial productivo.

## 7. Literatura y diferencia con nuestra adaptación

1. Bennell, J. A.; Song, X. (2010). *A beam search implementation for the irregular
   shape packing problem*. Journal of Heuristics 16(2), 167–188.
   [DOI](https://doi.org/10.1007/s10732-008-9095-x),
   [registro de universidad](https://researchportal.port.ac.uk/en/publications/a-beam-search-implementation-for-the-irregular-shape-packing-prob/).
   El resumen publicado describe búsqueda sobre el orden de piezas con heurística
   de placement y no-fit polygon. Aquí fijamos el orden y buscamos placements raster.
2. Bennell, J. A.; Cabo Nodar, M.; Martínez-Sykora, A. (2018). *A beam search approach
   to solve the convex irregular bin packing problem with guillotine cuts*.
   EJOR 270(1), 89–102. [DOI](https://doi.org/10.1016/j.ejor.2018.03.029),
   [registro y manuscrito aceptado](https://eprints.whiterose.ac.uk/id/eprint/134687/).
   Su problema combina piezas convexas, varios tamaños de bins y cortes guillotina.
   M6 incorpora círculos y prioridad de retazos; no incorpora esa restricción de cortes.
3. Fontan, F.; Libralesso, L. (2020). *An anytime tree search algorithm for
   two-dimensional two- and three-staged guillotine packing problems*.
   [Preprint v2](https://arxiv.org/abs/2004.02603v2),
   [DOI del preprint](https://doi.org/10.48550/arXiv.2004.02603).
   Contexto de búsqueda en árboles para cutting; no se atribuye su algoritmo anytime a M6.

Consulta verificable realizada el 02/11/2026 mediante fuentes primarias. La descripción
de 2010 se sustenta en el resumen y registro editorial universitario; no se afirma
haber replicado o verificado íntegramente su implementación. Los DOI y repositorios
son referencias; no se redistribuyen PDFs. La evidencia de los artículos no demuestra
el desempeño de SP006-BS-v1.

## 8. Faltantes y decisiones pendientes

Los tres fixtures sí contienen todos los parámetros geométricos y residuales necesarios:
no se rellenaron valores ausentes ni se inventaron casos oficiales. No se encontró
en esta integración una SPEC de SP-006/M6 con función de score, SLA, umbral de mejora
o presupuesto productivo aprobado. La mención histórica SP-006 en ADR-001 corresponde
al marco arquitectónico, no define esta heurística. Esta solicitud del usuario delimita
el spike y este documento registra las decisiones propuestas.

Falta acordar: criterio de aceptación entre completitud/merma/fuentes/costo; instancias
representativas a escala industrial si se necesita ese alcance; presupuesto de admisión
y concurrencia para la futura integración; revisión humana de los resultados Colab.
Los límites de este documento son propuestas explícitas de investigación.
No se exige inventar esos datos para ejecutar los tres fixtures existentes.

Los tiempos históricos de TA-027 son pruebas de sanidad y no se importan como mediciones.
Los archivos de `evidence/local-cpu-*` provienen de la ejecución real del notebook local;
las ejecuciones en Colab producirán su propio `origin=measured_colab_cpu` y timestamp.
