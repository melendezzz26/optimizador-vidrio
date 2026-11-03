# SPEC-TA-053 T01 - M6 Beam Search acotada

## Identificacion

| Campo | Valor |
|---|---|
| Codigo | TA-053 T01 |
| Responsable | Fabricio Melendez |
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
interrumpe la expansion, se conserva la ultima frontera completa y se devuelve
la razon de parada junto con el resultado parcial.

## Requisitos funcionales

- **RF-01:** ejecutar M6 sin invocar FF, BF o WF.
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
5. M6 produce decisiones propias; no delega en FF/BF/WF.
6. La igualdad con SP-006 se demuestra cuando se usan los mismos fixtures y
   configuracion, sin inventar evidencia de Colab.
7. El resultado parcial y `NO_FIT` no se presentan como solucion completa.
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
