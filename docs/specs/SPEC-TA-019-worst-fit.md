# SPEC-TA-019 — Worst Fit

## Información general

| Campo | Valor |
|---|---|
| ID | TA-019 |
| Nombre | Worst Fit |
| Sprint | Sprint 2 |
| Tipo / épica | Tarea técnica / EP-003 Optimización |
| Estado | **Reviewed** |
| Responsable | Fabricio Melendez |
| Revisor | Pendiente de asignación formal |
| Fecha | 25/10/2026 |
| Rama | `feature/TA-019-worst-fit` |
| Dependencias | SP-002; TA-016; motor First Fit existente; motor geométrico/raster existente; TA-037 como guardrail técnico cuando corresponda |
| PLAN técnico | [PLAN-TA-019-worst-fit.md](PLAN-TA-019-worst-fit.md) |

Este documento formaliza las decisiones funcionales autorizadas para TA-019
T01/T02 y pasa a Reviewed por aprobación del responsable comunicada en esta
sesión. CA-01 a CA-22 están técnicamente satisfechos: 22 PASS / 0 PARTIAL /
0 FAIL, con 381 pruebas aprobadas y evidencia reproducible. La revisión cruzada
real y la asignación de revisor permanecen pendientes. No se declara Verified;
el cierre posterior al versionado/PR sigue pendiente. La implementación anterior
a esta formalización se contrasta en el PLAN y no es fuente de requisitos.

## 1. Objetivo

Incorporar Worst Fit como política determinista de selección de fuente física,
reutilizando el motor geométrico de First Fit. TA-019 no crea un segundo motor
geométrico ni busca deliberadamente la peor solución global. La comparación
entre fuentes debe usar la capacidad libre posterior a una colocación canónica.

Esta SPEC es la fuente normativa de TA-019. El PLAN define su ejecución técnica
y evidencia; no introduce funcionalidades adicionales. Se conserva la línea
base de [First Fit](SPEC-S1-optimization-first-fit.md),
[rasterización](SPEC-TA-005-TA-006-rasterizacion.md) y
[validación geométrica](SPEC-TA-007-validacion-geometrica.md).

## 2. Alcance

### Incluye

- Algoritmo de dominio WF y sus pruebas T01/T02.
- Preparación de instancia y orden vigente de piezas, sin redefinirlos.
- Rasterización, rotación compartida y validación geométrica existentes.
- Margen, separación, forma interior y estado de ocupación actuales.
- Retazos primero y selección WF dentro del primer nivel factible.
- Evaluación temporal no mutante y aplicación exclusiva del ganador.
- Resultados completos o parciales, determinismo y simulación sin consumo.
- Resultado de dominio compatible con `OptimizationResult` y trazabilidad de
  pedido, pieza, unidad y fuente física.
- Extracción mínima compartida necesaria para preservar FF y evitar duplicación.
- Slice backend de snapshots y stock reales, sin integrar WF a `/runs`.

### Fuera de alcance

- Best Fit y comparación simultánea FF/BF/WF.
- Selección TA-025 y persistencia experimental TA-026.
- UI o frontend multimétodo.
- Persistencia completa multimétodo y generalización completa HTTP/NDJSON.
- Cambios de BD, modelos SQLAlchemy y migraciones.
- Cambios en confirmación transaccional, RBAC o fórmulas de métricas.
- Modificar `domain/rotation.py`, implementar TA-016 o rotaciones propias WF.
- Modelo predictivo/ML, garantía de óptimo global o búsqueda de la peor posición.

## 3. Actor y precondiciones

**Actor:** motor de optimización backend; sin nueva interacción HTTP o UI.

**Precondiciones:**

- Instancia validada por la preparación existente, con configuración válida y
  snapshots desconectados de piezas y stock.
- Cantidades expandidas a unidades; grupos por `(tipo de vidrio, espesor)`.
- Stock compatible con identidades físicas únicas y orden estable aguas arriba.
- Máscaras de material/pieza a la misma resolución y orientaciones obtenidas
  del componente común. Los errores de precisión o recursos no son NO_FIT.
- SP-002 y TA-016 deben coordinar sus decisiones/contratos con esta política.
  La referencia formal de SP-002 está pendiente de vincular; no se declara cerrada.
- TA-037 es dependencia de coordinación para presupuestos globales, cuando
  corresponda; TA-019 conserva guardrails existentes sin resolver aquella tarea.

## 4. Entradas y datos

| Campo / dato | Formato | Regla |
|---|---|---|
| Problema | `OptimizationProblem` | Pedidos, grupos, configuración y snapshots existentes. |
| Orden de piezas | Secuencia preparada | Área DESC, mayor dimensión bbox DESC, pedido/pieza/unidad ASC, según preparación vigente. |
| Orden de grupos | Clave material | Tipo y espesor ASC, como en FF. |
| Fuente física | `(source, material_id, physical_unit_index)` | Un retazo representa una unidad; planchas respetan la cantidad expandida. |
| `stock_rank` | Índice ordinal | Orden recibido dentro del nivel; no reconstruir por ID, fecha o área en el dominio. |
| Orientaciones | Secuencia común | Orden determinista; `orientation_rank` es su índice. |
| Posición | `(row, column)` | Primera válida según el mecanismo geométrico existente. |
| Layout | Estado raster inmutable | Material interior, usable, occupied, blocked y separación existentes. |
| Salida | `OptimizationResult` compatible | Colocaciones válidas, faltantes y completitud; identidad WF solo de dominio. |

La prioridad entre tipos de fuente no altera su orden relativo interno. La
preparación puede conservar la partición estable retazo/plancha usada por FF.

## 5. Reglas de negocio y técnicas

### RN-01 — Preparación y geometría comunes

Reutilizar preparación, stock, máscaras, rasterización, orientaciones,
validación, margen y separación. No copiar esos motores ni sus reglas.

### RN-02 — Niveles de stock

1. Nivel 1: retazos compatibles y geométricamente factibles.
2. Nivel 2: planchas compatibles, solo si ningún retazo aloja la pieza actual.

WF opera exclusivamente dentro del primer nivel con candidatos factibles. Una
plancha más grande no desplaza un retazo factible. No se introduce una prioridad
nueva de planchas abiertas frente a planchas sin usar.

### RN-03 — Colocación canónica por fuente

Cada fuente aporta como máximo un candidato: primera orientación factible de
la secuencia compartida y primera posición válida de esa orientación. No se
comparan otras posiciones u orientaciones de la misma fuente para cambiar el
score. Factibilidad requiere validar la geometría real, no solo su bbox o área.

### RN-04 — Score posterior exacto

Para un candidato `c`, sea `L'_c` el layout temporal obtenido al aplicar su
colocación mediante la operación inmutable existente. Se define:

```text
remaining_free_cells_after_placement(c)
    = suma por fila de popcount(usable(L'_c) AND NOT blocked(L'_c))
```

El score es un entero en celdas, no un porcentaje ni una métrica de residuo
recuperable. Usa ocupación y separación posteriores y respeta el margen y la
forma interior del material. No puede sustituirse por la capacidad previa.
La capacidad libre total puede estar fragmentada; no garantiza espacio contiguo.

### RN-05 — Selección y desempates

Seleccionar por: mayor score posterior; menor `stock_rank`; menor
`orientation_rank`; menor fila; menor columna. Equivale a minimizar:

```text
(-remaining_free_cells_after_placement, stock_rank, orientation_rank, row, column)
```

### RN-06 — Inmutabilidad y retención acotada

Evaluar un candidato no cambia el layout real. Solo el ganador se incorpora al
estado del cálculo. Los candidatos deben consumirse incrementalmente; la
cantidad de layouts temporales retenidos no debe crecer linealmente con el
número de fuentes. Esto no impone un nuevo presupuesto global de bytes: se
conservan los límites existentes y se coordina su evolución con TA-037.

### RN-07 — Compatibilidad y resultado

FF debe conservar su evaluación perezosa, salida temprana, placements, eventos
y resultados parciales. WF conserva pedidos múltiples, multimaterial, cantidad
física disponible y preparación vigente. Si una pieza no cabe, queda faltante y
se continúan intentando las siguientes. No se fabrican placements ni stock.

El dominio entrega completitud/faltantes; la orquestación existente conserva el
tratamiento `SIN_SOLUCION`. Esta tarea no introduce una corrida WF HTTP ni una
nueva confirmación. Las fórmulas de métricas, confirmación actual y RBAC siguen
vigentes sin cambios. Simular no consume, reserva ni modifica inventario.

### RN-08 — Determinismo

La misma instancia, snapshot de stock, configuración y versión del criterio
deben producir las mismas colocaciones y resultado geométrico. No se exige
igualdad de timestamps, IDs de corrida o tiempo computacional.

## 6. Flujo principal

1. Recibir y normalizar la instancia mediante la preparación existente.
2. Recorrer grupos y piezas en su orden vigente.
3. Obtener las orientaciones mediante el componente compartido.
4. Generar candidatos canónicos factibles del nivel de retazos.
5. Evaluar sus layouts posteriores temporales y seleccionar según RN-05.
6. Solo si no existe candidato de retazo, repetir con planchas.
7. Incorporar únicamente el ganador y emitir los hitos correspondientes.
8. Si no existe ganador, conservar la pieza faltante y continuar.
9. Devolver el resultado de dominio completo o parcial, sin mutaciones de stock.

## 7. Flujos alternativos y errores

- Stock vacío, fuentes incompatibles o ninguna colocación válida: pieza faltante.
- Varias fuentes equivalentes: resolver por RN-05, sin azar.
- Una pieza no colocable no impide intentar las posteriores.
- Error de raster, precisión, configuración o recursos: propagar el error
  existente; no convertir un fallo técnico en resultado geométrico NO_FIT.
- WF de dominio no se entrega a los adaptadores actuales exclusivos FF. Su
  integración y persistencia multimétodo requieren tareas posteriores.

## 8. Criterios de aceptación

| CA | Criterio verificable | Tarea |
|---|---|---|
| CA-01 | WF existe como política de dominio independiente. | T01 |
| CA-02 | Reutiliza el motor geométrico existente, sin duplicarlo. | T01 |
| CA-03 | No incorpora lógica propia de rotación ni modifica `rotation.py`. | T01/T02 |
| CA-04 | Retazos tienen prioridad sobre planchas según RN-02. | T01/T02 |
| CA-05 | Solo se consideran fuentes geométricamente factibles. | T01/T02 |
| CA-06 | Cada fuente usa su primera orientación factible y primera posición válida. | T01/T02 |
| CA-07 | El score usa capacidad libre posterior, incluyendo el efecto de la separación. | T01/T02 |
| CA-08 | WF selecciona el mayor score dentro del nivel permitido. | T01/T02 |
| CA-09 | Los desempates siguen exactamente RN-05. | T01/T02 |
| CA-10 | Evaluar candidatos no modifica el layout real. | T01/T02 |
| CA-11 | Solo el candidato ganador se incorpora al cálculo. | T01/T02 |
| CA-12 | Los layouts temporales retenidos no crecen linealmente con las fuentes evaluadas. | T01/T02 |
| CA-13 | FF conserva evaluación perezosa y salida temprana, sin calcular scores. | T01/T02 |
| CA-14 | La simulación WF no consume ni modifica inventario. | T01/T02 |
| CA-15 | La misma entrada produce las mismas colocaciones y resultado geométrico. | T01/T02 |
| CA-16 | Funciona cuando una rotación compartida es necesaria para colocar. | T02 |
| CA-17 | Funciona con margen y separación vigentes. | T02 |
| CA-18 | Respeta geometrías irregulares mediante el material interior real. | T02 |
| CA-19 | Respeta grupos multimaterial sin cruces de tipo o espesor. | T02 |
| CA-20 | Maneja piezas no colocables sin placements inválidos; conserva faltantes y continúa. | T01/T02 |
| CA-21 | No introduce migraciones ni cambios de esquema. | T01/T02 |
| CA-22 | Las pruebas aplicables de regresión de FF permanecen correctas. | T02 |

## 9. Impacto técnico y compatibilidad

- **Módulos:** dominio Optimization y pruebas unitarias/slice backend. Extracción
  compartida mínima, con imports compatibles para consumidores existentes.
- **API y NDJSON:** sin generalización ni cambios de contrato. Preservar eventos
  de FF y sus consumidores actuales.
- **BD / migración / inventario:** sin cambios de esquema o escrituras de cálculo.
- **UI, confirmación y RBAC:** sin cambios.
- **Métricas:** reutilización de fórmulas y validación existentes; sin nuevas métricas.
- **TA-016:** conservar secuencia determinista de orientaciones y coherencia entre
  ángulo, contorno local y máscara; coordinar también consumidores de métricas y
  revalidación de confirmación, sin modificarlos en TA-019.

## 10. Pruebas previstas

Unitarias: fuente WF clara; empate y desempates; score posterior frente al
previo; varias piezas; rotación necesaria; no colocable/parcial; retazo primero;
WF entre retazos; fallback a plancha; unidades físicas; margen; separación;
geometría irregular; multimaterial; multipedido; determinismo; no consumo; y
regresión explícita de lazy evaluation/salida temprana de FF.

Añadir protección reproducible de retención acotada con casos pequeños, sin
cargas masivas ni OOM. El slice permitido recorre snapshots/pedidos, stock,
preparación, WF y resultado de dominio. La matriz de pruebas está en el PLAN.

## 11. Evidencias requeridas

- Comandos, entorno, entradas pequeñas verificables y resultados reales de pytest.
- Regresión de score: pieza 1×1, resolución 1, separación 1, margen 0; fuente
  4×4: 16 celdas previas y 12 posteriores; fuente 1×15: 15 previas y 13 posteriores.
  Debe ganar 1×15.
- Evidencia de no consumo y preservación FF; auditoría de retención de layouts.
- `git diff --check`, diff de alcance y trazabilidad CA → pruebas.
- Evidencia del cierre técnico en [README](../evidence/sprint-02/TA-019/README.md),
  con salida real de la suite final y de `git diff --check`. La matriz del PLAN
  registra CA-01 a CA-22 técnicamente satisfechos: 22 PASS / 0 PARTIAL / 0 FAIL.
  La aprobación del responsable está registrada; la revisión cruzada sigue pendiente.

## Historial de estado

| Fecha | Estado | Nota |
|---|---|---|
| 25/10/2026 | Draft | Formalización de decisiones autorizadas; revisión formal pendiente. Reemplaza el documento informal `TA-019-worst-fit.md`. |
| 25/10/2026 | Draft | Evidencia técnica vinculada y CA-12 verificado; sin cambios de requisitos ni aprobación formal. |
| 25/10/2026 | Reviewed | Aprobación del responsable comunicada en esta sesión; 22 CA satisfechos, 381 pruebas aprobadas y evidencia vinculada. Revisión cruzada pendiente; no Verified. |
