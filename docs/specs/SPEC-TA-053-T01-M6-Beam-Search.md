# SPEC-TA-053 T01 - M6 Beam Search acotada

## Identificacion

| Campo | Valor |
|---|---|
| Codigo | TA-053 T01 |
| Responsable | Fabricio Melendez |
| Revisor humano esperado | Andro Joseph Quispe Cesias; el PR #91 no registra una review aprobatoria al 2026-11-02 |
| Dependencia | SP-006 |
| Heuristica | M6 - Beam Search acotada (BS-k) |
| Estado | Implementada y validada; TA-053 T02 completada en `test/TA-053-m6-beam-search` |
| Rama | `feature/TA-053-m6-beam-search-integrated` |
| Base | `origin/integration/sprint-01` |

La fuente normativa del algoritmo es `experiments/sp-006-m6/sp006/beam.py`,
version `SP006-BS-v1`, y su metodologia. El experimento es evidencia de
diseno, no una dependencia de ejecucion del backend.

## Objetivo

Incorporar M6 como un optimizador de dominio independiente que explore estados
parciales y conserve los mejores `k` estados por nivel. Debe reutilizar los
contratos, rasterizador, orientaciones, validacion de `SheetLayout`, metricas y
preparacion existentes. FF, BF y WF, su coordinador publico, el contrato de
comparacion, la UI y M4/M5 quedan fuera de esta tarea.

## Alcance

Incluye el motor M6 en dominio, su adaptador de application, pruebas unitarias
de algoritmo y regresiones de contrato/inmutabilidad. Incluye la configuracion
inicial `k=2`, limites de busqueda verificables y documentacion de evidencia.

Excluye endpoints, persistencia, migraciones, consumo de inventario, frontend,
coordinacion publica de seis motores, cambios a FF/BF/WF, M4, M5 y el conjunto
exhaustivo de pruebas de TA-053 T02.

## Contrato y entradas

M6 recibe un `OptimizationProblem` ya preparado, con unidades expandidas,
grupos por `(glass_type_id, thickness_mm)`, stock compatible y una
`OptimizationConfig`. Devuelve un `OptimizationResult` con las mismas
`Placement`, identidades y geometria orientada que los motores existentes.
El resultado es una simulacion: layouts y problemas son inmutables y no se
modifica inventario.

Se admiten RECTANGULO, CIRCUNFERENCIA y POLIGONO_CONVEXO. La resolucion se
mantiene en 1 mm en los casos experimentales; el motor respeta la resolucion
de la configuracion. Las orientaciones se generan con el paso configurado
(5 grados en los fixtures), se deduplican por mascara y conservan el primer
angulo.

## Diseno algoritmico

### Estado

Cada nodo inmutable contiene:

- un layout por fuente fisica, en orden estable, incluyendo fuentes aun no
  usadas;
- placements aceptados;
- traza determinista de decisiones;
- unidades procesadas.

Los layouts nuevos se obtienen con `SheetLayout.place`; no se mutan estados
anteriores ni se comparten caches entre ejecuciones.

### Expansiones

1. Ordenar grupos por clave material y unidades con la preparacion comun.
2. Para cada unidad, certificar exhaustivamente primero todos los retazos
   compatibles. Solo si ninguno es geometricamente factible se examinan
   planchas.
3. Para cada fuente factible y orientacion, generar la primera posicion valida
   en orden fila/columna.
4. Generar tambien la ultima posicion valida mediante recorrido inverso. Si
   coincide con la primera, producir una sola rama.
5. Si ninguna fuente cabe, producir un hijo `NO_FIT` sin placement y continuar
   con la siguiente unidad. Un limite agotado produce una terminacion de
   recursos, nunca una conclusion geometrica de ausencia de solucion.

Las decisiones usan las mascaras reales de piezas y materiales, margen,
separacion y limites de `SheetLayout`. No se reemplaza la geometria por AABB
para aceptar una colocacion.

### Puntuacion y poda

Se minimiza lexicograficamente:

```text
(processed - placements,
 -area nominal colocada,
 planchas fisicas usadas,
 area nominal de fuentes usadas,
 -maximo rectangulo libre en celdas,
 envolvente ocupada en celdas,
 traza completa)
```

Se conservan como maximo 12 hijos por padre y los `k` mejores nodos globales
por nivel. `k=2` es la configuracion de produccion inicial. Los empates se
resuelven por la traza `(decision, fuente, orientacion, fila, columna)`.
No se invoca ningun optimizador baseline.

### Limites

Los defaults de T01 son los validados por SP-006: ancho 2, 12 hijos por padre,
2 posiciones por orientacion, 60000 expansiones, 1000000 sondeos geometricos,
32 MiB de estado retenido y 30 s por corrida. Los limites deben inyectarse y
su agotamiento debe distinguirse de `NO_FIT`. La preparacion conserva ademas
los limites internos de `RasterCache`; no se amplian.

Una frontera se reemplaza solo despues de completar el nivel. Si un limite
interrumpe la expansion, se conserva la ultima frontera completa.

**Respaldo al detenerse (v1.1, S2-M6).** Si un limite (`TIME_LIMIT`,
`EXPANSION_LIMIT`, `GEOMETRY_PROBE_LIMIT` o `STATE_MEMORY_LIMIT`) detiene la
busqueda, M6 completa las unidades restantes desde el mejor nodo con la regla
First Fit y lo registra en el diagnostico. Detalle:

- Se parte de los layouts del mejor nodo de la ultima frontera completa; las
  unidades que M6 ya decidio (colocadas o `NO_FIT`) se conservan tal cual.
- La decision de cada unidad restante es la de First Fit en
  `packing._feasible_candidates` (retazos antes que planchas, orden del stock,
  primera orientacion con posicion); se reutiliza, no se duplica. Los layouts
  usados se cobran al mismo tope de 128 MiB que `pack()` (`_retain_layout`,
  extraido en v1.2 sin cambiar FF).
- Desde ese momento solo rige el checkpoint del supervisor (cancelacion y
  presupuesto por motor); los contadores y el reloj propios de M6 ya se
  agotaron.
- Si todas las unidades se procesan, la razon de parada se omite y el
  adaptador deriva `COMPLETED` o `NO_FIT` como en cualquier corrida; el
  contrato v2 no cambia.
- El diagnostico agrega, solo cuando hubo respaldo: `fallback_used = 1`,
  `fallback_from_<limite> = 1`, `fallback_beam_units` (unidades decididas por
  M6) y `fallback_units` (unidades decididas por el respaldo). La UI lo muestra
  en "Detalles del metodo".
- `BeamSearchLimits.complete_on_stop` (por defecto `True`) permite desactivarlo:
  con `False` se conserva el comportamiento T01, resultado parcial junto con la
  razon de parada. Las pruebas de limites lo usan para seguir verificando ese
  camino.
- Las corridas que terminan dentro de los limites no cambian: mismo resultado,
  traza y estadisticas.

Motivo: asignado por el equipo tras la revision del 04/11/2026: M6 no colocaba
piezas con planchas reales (por ejemplo, 1 pieza de 1000x2500 sobre un retazo
de 2440x3255 terminaba 0/1 por `TIME_LIMIT`, mientras los otros cinco motores
la colocaban en milisegundos).

**Rendimiento sin cambiar decisiones (v1.2 y v1.3, S2-M6).**

- v1.2: las fuentes con el mismo raster comparten un unico layout vacio
  inmutable, y `initial_bound` lo cobra una vez por material distinto. La
  memoria de estado durante la busqueda se mide de forma incremental: la base se
  recorre una vez por padre y cada hijo una vez. El valor es siempre mayor o
  igual que `graph_bytes`, y hay una prueba que lo compara en cada verificacion.
  El puntaje de una colocacion sobre un layout vacio compartido se calcula una
  vez por nivel.
- v1.3: `metrics.largest_rectangle`, compartida por M5, M6 y `calculate_metrics`,
  recorre tramos de columnas iguales en lugar de cada columna. Devuelve
  exactamente la misma tupla y el mismo orden de desempate. La prueba de
  equivalencia la compara contra la implementacion anterior.
- Las decisiones, la traza y los contadores de busqueda no cambian:
  `test_beam_search_t02.py` y la evidencia SP-006 siguen iguales.

**Limite conocido.** Con piezas rotadas a 5 grados sobre planchas de
2140x3300 a 1 mm, cada puntaje cuesta unos 0,24 s, porque los bordes cambian en
casi cada columna. En 30 s M6 evalua unos 117 sucesores, asi que decide muy
pocas unidades (1 de 6 en la carga de 6 piezas; 0 con 46 y con 100) y el
resultado lo completa el respaldo First Fit.

**Mejora futura (fuera de alcance).** Redisenar el puntaje de M6, de forma
aproximada o en dos etapas. Cambia sus decisiones, asi que exige rehacer la
evidencia SP-006 con Fabricio Melendez. Evidencia de carga:
[S2-WF-CARGA, seccion 7](../evidence/sprint-02/S2-WF-CARGA/README.md#7-m6-beam-search-antes-y-después).

## Requisitos funcionales

- **RF-01:** ejecutar la busqueda M6 sin invocar los optimizadores FF, BF o WF.
  Solo si un limite detiene la busqueda, las unidades restantes se completan con
  la regla de decision de First Fit (ver "Respaldo al detenerse", v1.1).
- **RF-02:** soportar las tres geometrias canonicas existentes.
- **RF-03:** respetar resolucion de 1 mm cuando asi lo configure el caso.
- **RF-04:** enumerar rotaciones en pasos de 5 grados en la configuracion SP-006.
- **RF-05:** aplicar margen, separacion y validacion raster existentes.
- **RF-06:** priorizar retazos compatibles y geometricamente factibles.
- **RF-07:** producir el mismo resultado ante entradas identicas.
- **RF-08:** continuar tras unidades no colocables y distinguirlas de limites.
- **RF-09:** mantener la simulacion sin mutar inventario.
- **RF-10:** devolver el contrato `OptimizationResult` sin alterar schemas publicos.

## Requisitos no funcionales

El motor debe ser determinista, puro respecto de stock/pedidos, compatible con
el supervisor Linux/WSL2 existente y controlable por checkpoints. La memoria se
limita mediante la cota conservadora de estados y los limites de cache
existentes. Las estadisticas de expansiones, sondeos, padres, poda, frontera
maxima y razon de parada deben ser observables por pruebas sin introducir una
API publica nueva.

## Criterios de aceptacion

1. SMALL, MEDIUM y COMPLEX producen placements validos y deterministas.
2. Se conservan identidades de pieza/unidad, fuente, posicion y rotacion.
3. No existen superposiciones ni violaciones de margen/separacion.
4. Los retazos factibles se prueban antes que las planchas.
5. M6 produce decisiones propias mientras su busqueda no se detenga; si un
   limite la detiene, completa las unidades restantes desde el mejor nodo con la
   regla First Fit y lo registra en el diagnostico (`fallback_*`).
6. La igualdad con SP-006 se demuestra cuando se usan los mismos fixtures y
   configuracion, sin inventar evidencia de Colab.
7. El resultado parcial y `NO_FIT` no se presentan como solucion completa. Un
   resultado completado por el respaldo First Fit si es completo (todas las
   unidades colocadas) y se identifica como tal en el diagnostico y en la UI;
   con `complete_on_stop=False` se conserva el resultado parcial con su razon.
8. La entrada y el inventario permanecen sin mutaciones.
9. FF/BF/WF y el coordinador publico no cambian.
10. Los limites de tiempo, expansiones, sondeos y memoria son reproducibles.

## Estado de cumplimiento T01

Los criterios de T01 se verificaron con los fixtures oficiales y regresiones
del backend. Al cierre de T01, antes de completar T02, la suite no supervisada
de Windows paso 495 pruebas; en WSL2 con PostgreSQL aislado pasaron 861 pruebas
de optimizacion/API/integracion y 14 pruebas del supervisor. La suite portable
de SP-006 paso 47 pruebas. T02 amplio luego las suites relacionadas; sus conteos
actualizados y el detalle de cada ejecucion estan en la
[evidencia TA-053 T02](../evidence/sprint-02/TA-053-T02/README.md). Estos conteos
pertenecen a suites solapadas y no deben sumarse. No se ejecuto una sesion real
de Google Colab en esta tarea, por lo que la evidencia local de SP-006 no se
presenta como medicion de Colab.

Las pruebas exhaustivas de TA-053 T02 se completaron en su rama dedicada. La
integracion publica de M6 y TA-043 siguen fuera de alcance.

## Riesgos y mitigaciones

| Riesgo | Mitigacion |
|---|---|
| Clonacion de layouts por nodo | layouts inmutables, cache por corrida y cota de bytes |
| Explosion de candidatos | 12 hijos por padre, posiciones primera/ultima y beam global |
| Confundir limite con NO_FIT | razon de parada explicita y frontera anterior completa |
| Desviacion del experimento | pruebas de paridad con los tres fixtures y traza determinista |
| Mutacion accidental de stock | contrato read-only y prueba de snapshots antes/despues |
| Afectar otros motores | modulo independiente y regresion enfocada de FF/BF/WF |
| Respaldo confundido con busqueda propia | contadores `fallback_*` en el diagnostico y etiqueta en "Detalles del metodo" |

## Historial de estado

| Fecha | Version | Estado | Cambio |
|---|---|---|---|
| Fecha a confirmar por Fabricio Melendez | 1.0 | Implemented | T01/T02: M6 Beam Search acotada integrada (Fabricio Melendez). |
| 2026-11-07 | 1.1 | Implemented | S2-M6 F1 (Fabricio Aguilar, rama `fix/S2-m6-rendimiento`): respaldo First Fit al detenerse por un limite (`complete_on_stop`), contadores `fallback_*` y etiqueta en la UI. Se versionaron RF-01, CA-5, CA-7 y "Limites". Asignado por el equipo tras la revision del 04/11/2026: M6 no colocaba piezas con planchas reales. Carga 6/46/100: de 0/6 (`TIME_LIMIT`) y 0/46, 0/100 (`STATE_MEMORY_LIMIT`) a 6/6, 46/46 y 100/100. |
| 2026-11-07 | 1.2 | Implemented | S2-M6 F2: layout vacio compartido por material, `initial_bound` por material distinto, medicion incremental de memoria (siempre >= `graph_bytes`), puntaje reutilizado sobre layouts vacios compartidos, tope de 128 MiB de `pack()` en el respaldo. Con 46 y 100 piezas desaparece `STATE_MEMORY_LIMIT`; el perfil paso de 63 % del tiempo en `graph_bytes` a 95 % en `largest_rectangle` (0,38 s por llamada). |
| 2026-11-07 | 1.3 | Implemented | S2-M6 F4b: `metrics.largest_rectangle` por tramos de columnas, con resultado identico. 0,38 s a 0,24 s por llamada; en 30 s M6 pasa de 75 puntajes calculados (perfil F4a) a 117 sucesores evaluados y decide 1 de 6 unidades (antes 0). M5 con 46 piezas: 96,9 s a 38,4 s, con el mismo resultado. Limite conocido y mejora futura documentados. |
