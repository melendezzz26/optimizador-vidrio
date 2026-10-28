# SPEC-HU-017 — Visualizar proceso de optimización

## Información general

| Campo | Valor |
|---|---|
| ID / nombre | HU-017 — Visualizar proceso de optimización |
| Estado | **Verified — local, sin integrar** |
| Tipo / módulo | Historia de usuario / Optimization |
| Responsable / revisor | Implementación y verificación local: Codex por encargo del solicitante. Responsable/revisor humano formal pendientes. |
| Fecha | 28/10/2026 UTC |
| Base inspeccionada | `4bcf54d`, `integration/sprint-01`; antecedente documental `783aac8` |
| Ejecución | T01–T06 implementadas y verificadas en `feature/HU-017-proceso-visual-optimizacion`, con commits y evidencia local. Sin push, PR ni merge. |
| PLAN | [PLAN-HU-017-proceso-visual-optimizacion.md](PLAN-HU-017-proceso-visual-optimizacion.md) |
| Dependencias | HU-015/S1-01, SP-001, TA-016, TA-018, TA-019, TA-021 y TA-037 según contratos pendientes |
| Decisión | Cierre técnico local autorizado y probado con PostgreSQL temporal para esta HU. Revisión cruzada humana e integración pendientes; sin cambiar backlog remoto. |
| Streaming / DG-01 | **B implementada; DG-01 Closed.** Perfil visual-v2 optativo, V1 predeterminado; contrato en [DECISION-HU-017-DG-01](DECISION-HU-017-DG-01-streaming-visual.md). |
| Evidencia de cierre | [T03–T06, matriz de 26 CA, pruebas, recursos y capturas](../evidence/sprint-02/HU-017/t03-t06-visualizacion-y-cierre-local.md). |

## 1. Identificador, historia y propósito

Antes de crear este documento se buscaron HU-017/HU017/HU_017 en los archivos
del repositorio, mensajes de commits de todas las referencias locales, nombres
históricos de archivos y cambios de texto de `docs/`. No se encontró una historia
asignada a HU-017. La única mención previa es la nota de disponibilidad histórica
de [HU-016](SPEC-HU-016-dashboard-inicial.md), commit `f5e9e79`; no es una colisión.
La disponibilidad comprobada es local, sin afirmar reserva en el backlog externo.

**Historia:** Como operario, quiero visualizar las etapas de preparación,
rasterización, rotación y colocación de las piezas durante la optimización,
para comprender cómo se construye la distribución propuesta antes de confirmar
el resultado.

**Propósito:** un único flujo visible:

`Pedido(s) → resolución única y geometrías válidas → bases listas y configuración congelada → heurística (orientaciones y posiciones bajo demanda) → resultado`

La rasterización es una etapa de Optimización, no un trabajo previo independiente
que el operario deba ejecutar. La visualización explica hechos reales, sin alterar
las decisiones de FF/BF/WF ni atribuir al contrato HTTP métodos aún no integrados.
HU-017 es consumidor visual de resultados/eventos. La comparación/orquestación
de FF/BF/WF sobre la misma instancia corresponde a TA-021 y no selecciona un
método ganador. HU-017 tampoco decide ese ganador.

## 2. Contexto y auditoría de la base

Revalidación del 27/10 sobre `4bcf54d`: FF/BF/WF comparten `packing.pack` y
`RasterCache.orientations`; BF ya existe en dominio. TA-021 está Verified/Closed
y compara los tres métodos internamente, sin ganador. El ciclo HTTP de corridas
y sus parsers V1 siguen entregando FF. TA-037 tiene SPEC y guardrails integrados;
la preparación previa de bases y el consumo incremental de orientaciones siguen
pendientes. Estos cambios de contexto no modifican los 26 CA aprobados.

| Fuente actual | Hallazgo relevante |
|---|---|
| `OptimizationPage.jsx` | Ya pertenece a Optimization. Alterna `first-fit` y `hu015` mediante «Distribución de corte» / «Vista previa de piezas». Esta última es la separación visible que se debe fusionar. |
| `Sidebar.jsx`, `App.jsx` | Ya existe una sola entrada `optimization`, «Optimización». No hay una entrada Sidebar «Rasterización» que deba inventarse para eliminarla. |
| `runApi.prepare`, `useFirstFit`, reducer | Recuperan pedidos y grupos; el adaptador real prepara `rasters: {}`. No hay preparación global real de máscaras en esa fase. Algunos rótulos de etapas no tienen eventos backend equivalentes. |
| HU-015 y `useOptimization` | Selector de un pedido/pieza y resolución independiente. Baseline de preview 5 mm; respuestas obsoletas se cancelan/ignoran. |
| `AcceptRun.execute` | Valida lote/configuración y tamaños; crea snapshot/corrida y pasa pedidos a EN_OPTIMIZACION atómicamente. No rasteriza todas las geometrías. |
| `CalculateRun.execute`, `packing.pack` | Stock previo al cálculo; orientaciones por pieza y materiales bajo demanda mientras avanza la búsqueda. No existe barrera previa de máscaras base. FF usa `next()`; WF compara candidatos canónicos con score posterior. `RasterCache.orientations()` devuelve actualmente una tupla por pieza: la generación incremental por orientación requiere coordinación con TA-016. |
| `run_stream`, `run_schemas`, `runContract` | Ocho eventos V1, método FF; sin máscaras, intentos de orientación ni evento individual de faltante. Los parsers son estrictos. |
| `PlacementCanvas`, `PlacementScene3D`, `RasterInspection` | Vistas 2D/3D/raster reutilizables; en el flujo real pueden faltar máscaras en el snapshot del frontend. No equivalen a telemetría de orientaciones evaluadas. |
| `metrics`, `domain/confirmation` | Métricas y residuales conservadores, revalidación raster del patrón persistido. No se encontró comprobación vectorial final de todas las colocaciones contra geometría original. |

La [revisión S1-01 de HU-015](SPEC-HU-015-interfaz-rasterizacion.md) prevalece sobre
sus descripciones históricas: preparar vista previa conserva PENDIENTE; el inicio
real es `/runs`. No se reabre ni altera el cierre histórico Verified de HU-015.

## 3. Alcance y exclusiones

### Incluye

- Unificación de experiencia en Optimization y reutilización de vistas HU-015.
- Etapas A–E, máscara autoritativa visible, orientación relevante, pieza/fuente
  actual, colocaciones aceptadas, faltantes y resultado recuperable.
- Preparación previa de máscaras base con resolución efectiva coherente;
  generación/evaluación de orientaciones y posiciones bajo demanda.
- Contrato visual NDJSON acotado y compatible; negociación/versionado concretos
  definidos en el PLAN, sin imponer un perfil específico en esta SPEC.
- Vista operativa y detalle técnico opcional; responsive, teclado y movimiento reducido.
- Preservación de pedidos múltiples, grupos materiales, margen, separación,
  retazos primero, métricas, snapshots existentes y confirmación explícita.
- Diseño de UI compartido para métodos que efectivamente entregue el backend.

### Fuera de alcance

- Nuevo algoritmo, reimplementación de FF/BF/WF o cambiar su selección por animación.
- Integrar por sí sola BF/WF a persistencia/confirmación, comparación simultánea
  o selección TA-025; mostrar método no implementa esas tareas.
- Modelo predictivo/ML, consumo/reserva de inventario durante simulación,
  infraestructura distribuida nueva, WebSockets o rediseño completo del sistema.
- Eliminar ahora rutas HU-015 o modificar su SPEC/evidencia histórica.
- Implementar validación vectorial final: se registra como GAP separable (§8).

## 4. Actor, permisos y datos

**Actor principal:** operario autorizado. Se conservan capacidades efectivas
`optimization.execute`, `optimization.view`, `optimization.confirm` y los accesos
de lectura de Orders que correspondan. No se concede permiso por mostrar una vista.

| Datos | Regla |
|---|---|
| Selección | Uno o varios pedidos pendientes, sin iniciar por abrir la pantalla. |
| Piezas | Identidad pedido/pieza/unidad; geometría persistida y cantidad originales. |
| Material | Grupo `(tipo de vidrio, espesor)` y fuente `(source, material_id, stock_unit_index)`. |
| Configuración | Snapshot geométrico congelado antes de FF/BF/WF: resolución efectiva, margen, separación, paso angular y reglas de normalización aplicables. |
| Preparación | Referencia inmutable de geometría/máscara/orientación ligada a corrida y resolución. |
| Progreso | Piezas procesadas y colocadas diferenciadas; no simular éxito de faltantes. |
| Resultado | Placements, faltantes, materiales usados, residuales, métricas disponibles y método real. |

No usar una respuesta del preview histórico leída de Orders en vivo como prueba
de que esa misma máscara corresponde al snapshot aceptado de la corrida.

## 5. Experiencia propuesta: etapas A–E

| Etapa | Vista operativa | Detalle técnico opcional |
|---|---|---|
| A — Selección | Pedidos, materiales/espesores, resumen de piezas, configuración aplicable; acción explícita para iniciar. | ID/configuración, resolución configurada y política aplicable. No inventar una API de configuración hoy ausente. |
| B — Preparación geométrica | Validando, normalizando y rasterizando máscaras base; máscara de la pieza actual y estado real de preparación. No indica que todas las orientaciones ya se generaron. | Resolución efectiva, dimensiones raster, celdas, cantidad, regla de ángulos permitidos y advertencia de aproximación. |
| C — Rotaciones | Geometría/máscara y ángulo realmente evaluado; transiciones representativas sin repetir artificialmente todos los ángulos. | Rango/índice de orientación y referencia de máscara; «muestra de evaluaciones» si hubo muestreo. |
| D — Evaluación | Pieza/unidad, fuente actual cuando esté informada, orientación, progreso; colocación aceptada o pieza sin ubicar. | Fuente física, método y score real cuando exista; FF no recibe un score ficticio. |
| E — Resultado | Distribución 2D/3D/raster, fuente, posición, orientación, piezas faltantes, métricas y sobrantes; acción separada de confirmar. | Método/configuración efectivos, unidades físicas y trazabilidad del snapshot. |

Los mensajes deben describir actividad observable. No marcar «rasterización
completada» por un temporizador ni mostrar una orientación muestreada como lista
exhaustiva. Las vistas 2D/3D son representaciones del patrón, no un nuevo cálculo.

**Accesibilidad:** diseño a 360/768/1440 px como escenarios de prueba, sin desborde
de acciones; tablas desplazables y canvas con viewport. Controles por teclado,
foco visible y devolución de foco al cerrar detalle/diálogo; estado textual y
`aria-live` moderado, sin anunciar cada intento. Respetar movimiento reducido;
pausar animación no debe pausar el algoritmo ni consumir inventario.

**Estados:** selección vacía, cargando pedidos/configuración, preparando,
evaluando, máscara pendiente/no disponible, resultado completo/SIN_SOLUCION,
error previo a aceptación, fallo técnico, desconexión y recuperación por ID.
No inventar un nuevo estado persistido CANCELADA. Cambiar selección invalida solo
previews locales previos; nunca altera una corrida ya aceptada.

## 6. Fusión HU-015 → Optimization y compatibilidad

- Conservar Sidebar «Optimización» e identidad `optimization` de navegación.
- Sustituir la bifurcación visible de `OptimizationPage` por el flujo A–E.
  La inspección raster pasa a panel integrado, sin selector ni inicio paralelo
  de pedido como prerrequisito del cálculo.
- Reutilizar `RasterComparison`, `GeometryPreview`, `RasterPreview`, canvas,
  `RasterInspection`, `InspectionViewport`, estados accesibles y manejo de
  respuestas obsoletas. Ya están en `features/optimization`: no requieren
  moverlos a otro módulo ni una migración física de directorios por sí misma.
- Descomponer la orquestación de `Hu015Rasterization`/`useOptimization` solo en
  la futura implementación; no copiar su selector/estado como segundo flujo.
- Mantener `POST /api/optimization/start` y `/rasterize` como contratos históricos
  compatibles, autenticados y de lectura, con su semántica S1-01. No son privados
  por eliminar su acceso visual ni deben convertirse en llamadas obligatorias
  de `/runs`. La retirada futura requiere decisión y consumidores auditados.
- `/start`: valida PENDIENTE, devuelve PENDIENTE; no crea corrida/reserva.
  `/rasterize`: conserva lectura PENDIENTE/EN_OPTIMIZACION y sus rechazos existentes.
  No ampliarlo silenciosamente a pedidos ya optimizados para pintar resultados.
- Recuperar resultados y máscaras del snapshot de corrida mediante un contrato
  visual propio cuando proceda; conservar GET canónico y confirmación actuales.
- Mantener HU-015 como historia, SPEC y evidencia histórica. Fusionar el flujo
  visible no elimina ni reescribe esos artefactos ni sus contratos compatibles.

## 7. Invariante de preparación y resolución raster

### RN-01 — Máscaras base listas; búsqueda y orientaciones perezosas

Antes de iniciar FF/BF/WF se debe completar esta secuencia verificable:

1. Fijar una única resolución efectiva, común y técnicamente válida para la corrida.
2. Validar geometrías y normalizarlas según las reglas compartidas existentes.
3. Preparar las representaciones/máscaras base necesarias del snapshot de piezas
   y materiales, compartiéndolas entre unidades/figuras idénticas.
4. Congelar la configuración geométrica aplicada: resolución, margen, separación,
   paso angular y reglas de normalización. Cambiar ajustes de UI o configuración
   vigente después no modifica la corrida aceptada.

`resolución única → geometrías válidas → bases listas → configuración congelada → FF/BF/WF`

Máscara base significa la representación normalizada de referencia, no el conjunto
completo de rotaciones. La normalización no reemplaza la geometría original
persistida. Congelar configuración no implica un esquema de BD nuevo.

La preparación previa no implica precomputar todas las orientaciones, posiciones,
candidatos o layouts. Durante la heurística las orientaciones y posiciones pueden
continuar generándose/cacheándose perezosamente mediante los componentes comunes.
La visualización no fuerza un nuevo contrato exhaustivo ni consume anticipadamente
esos iteradores. No generar orientaciones adicionales ni continuar buscando para
alimentar una animación.

FF conserva explícitamente lazy evaluation y salida temprana: no evalúa otras
fuentes, orientaciones o posiciones después del primer candidato factible ni
calcula scores. WF conserva su comparación entre fuentes, colocación canónica y
score posterior. La generación compartida debe preservar orden y deduplicación.

**Avance local T02:** `PreparedRunGeometry` prepara las bases antes de buscar,
y el componente común TA-016 ofrece una vista reiterable de orientaciones bajo
demanda. Se conserva la tupla histórica para sus otros consumidores. La
integración `4bcf54d` de partida todavía tiene el GAP; este avance solo existe en
la rama local de HU-017. [Evidencia del incremento](../evidence/sprint-02/HU-017/t02-bases-y-rotaciones-lazy.md).
Se conservan presupuestos TA-037 y fallos técnicos explícitos, sin omitir
candidatos ni reducir precisión. No se exige materializar todas las orientaciones
de la corrida. Contrato visual, referencias públicas y recuperación de máscaras
siguen pendientes de T03/T04, tras DG-01.

### RN-02 — Cuatro conceptos distintos

| Concepto | Situación actual / requisito |
|---|---|
| Resolución configurada | `Configuracion.resolucion_raster_mm`; corrida actual exige configuración vigente completa y no toma automáticamente el default raster. |
| Resolución mínima permitida | No existe un mínimo global de producto definido en el dominio; hoy exige >0 y presupuestos. La escala SQL de 0.001 mm no es una política de mínimo. Si se define un mínimo técnico con TA-037, se valida sin convertirlo en objetivo automático de selección. |
| Resolución efectiva | Una sola resolución fijada para toda la corrida y sus grupos, máscaras y placements. Hoy coincide con la configurada; debe conservarse en el snapshot/resultado. |
| Límites de recursos | Distinguir preview, cálculo y visualización; no intercambiar sus presupuestos ni asumir que un límite por máscara controla toda la corrida. |

Baseline atribuida a **SP-001** en SPEC-TA-005/006, `rasterizer.DEFAULT_RESOLUTION_MM`
y `useOptimization`: **5 mm/celda**. No se encontró un informe SP-001 separado con
resultados en `docs/spikes/`; se referencia la decisión incorporada, no se inventa
un estudio. El seed demo/E2E usa **1 mm**, que no es mínimo ni default universal.

Límites actuales observados, no objetivos nuevos: preview HU-015: 1 000 000
celdas, eje 2440, 128 vértices, payload 262 144 bytes; motor: 16 000 000 celdas
por máscara, eje 4000 celdas, dimensión 4000 mm, cache raster 64 MiB y layouts usados 128 MiB;
secuencia angular hasta 10 000 orientaciones. No hay presupuesto global aprobado
que cubra simultáneamente preparación, layouts temporales, JSON y renderizado.

Ejemplo: plancha 2140×3300 a 1 mm requiere 7 062 000 celdas: supera el preview
HU-015, aunque está bajo el límite individual de máscaras del motor. Eso no
garantiza que la corrida completa ni su representación JSON quepan.

### RN-03 — Una resolución efectiva validada, sin selección automática

HU-017 conserva la resolución configurada como resolución efectiva de la corrida,
validada contra los límites técnicos aplicables. No obliga a elegir la mínima,
la más fina ni un valor automático. Tampoco fija arbitrariamente 1 mm.

Fijarla antes de preparar máscaras base y mantenerla en todas las orientaciones,
materiales y placements, sin cambios por pieza ni adaptación a mitad de corrida.
Si no pasa el presupuesto, informar error técnico; no sustituirla silenciosamente
por otra ni convertir el problema de recursos en SIN_SOLUCION. Una eventual
selección automática de una resolución más fina queda como decisión/investigación
posterior coordinada con TA-037, fuera de esta historia. Se conserva la baseline
histórica de SP-001 sin convertirla en mínimo obligatorio.

## 8. Precisión, no solapamiento y GAP vectorial

La estrategia vigente usa máscaras conservadoras para piezas y máscaras interiores
para material; margen erosiona y separación dilata en celdas con redondeo hacia
arriba. `SheetLayout.check/place` valida límites y ausencia de ocupación/conflicto
en ese modelo. Las coordenadas se normalizan/redondean a seis decimales y las
rotaciones no ortogonales usan trigonometría: no es exactitud matemática continua.

La revalidación de confirmación reconstruye contornos/ángulos y métricas y
vuelve a comprobar el patrón raster. La validación de polígonos de Orders
comprueba geometrías individuales; no sustituye a comprobar todas las piezas
colocadas entre sí y contra su fuente original.

**GAP-VECTORIAL:** no se encontró validación final independiente vectorial de
contención, solapamiento y distancias sobre la geometría original transformada.
Se recomienda analizarla como defensa adicional, no como prueba de que hoy todo
sea inválido. Debe decidirse una tarea separable, sin ID nuevo asignado aquí:
transformaciones, círculos/polígonos, tolerancias, margen, separación y respuesta
a discrepancias. «Vectorial» tampoco equivale automáticamente a aritmética exacta.

La decisión debe determinar si será condición previa al resultado confirmable.
Si se adopta, un rechazo no permite mover piezas o cambiar de heurística en la
UI: se informa fallo/no confirmable según contrato aprobado. No se implementa
ni se atribuye esta garantía a HU-017 o a la confirmación existente.

## 9. Streaming visual propuesto

### RN-04 — Reutilizar y versionar

Reutilizar transporte NDJSON, envolvente `sequence`, `id_optimizacion`,
`occurred_at`, `event`, `data`, correlación por grupo/unidad y GET canónico.
Los ocho eventos V1 actuales permanecen sin cambios para consumidores existentes:
`optimization_started`, `group_started`, `piece_started`, `piece_placed`,
`group_completed`, `metrics_calculated`, `optimization_completed`, `optimization_failed`.

El contrato debe definir eventos, payloads, correlación, orden, compatibilidad
y límites de entrega. La comparación del PLAN se resolvió por elección expresa
del solicitante: **B, perfil visual-v2 optativo**, con V1 predeterminado.
[DG-01](DECISION-HU-017-DG-01-streaming-visual.md) concreta negociación,
versiones, entrega, referencias y presupuestos iniciales; su implementación y
pruebas quedan en T03. Esta concreción no altera los 26 CA funcionales.
No enviar tipos nuevos a un parser incompatible ni
degradar silenciosamente el contrato. El modo visual no modifica problema,
stock, resolución ni política heurística.

| Evento visual nuevo | Hecho y payload mínimo propuesto |
|---|---|
| `preparation_started` | Inicio real de preparación; totales, configuración/resolución efectiva y método disponible. |
| `piece_rasterizing` | Geometría única actual en preparación; referencia pedido/pieza, sin afirmar avance de placement. |
| `piece_ready` | Descriptor y referencia de máscara autoritativa; resolución, dimensiones, orientación de preview y cantidad. |
| `preparation_completed` | Máscaras base de piezas/materiales listas y referencia de preparación; no implica que todas las orientaciones se hayan generado. |
| `orientation_testing` | Muestra de evaluación real: unidad, fuente cuando aplique, ángulo/rango y referencia de máscara. No toda orientación generada fue evaluada. |
| `source_selected` | Fuente física ganadora y orientación; score con nombre/unidad solo si el método realmente lo expone. |
| `piece_unplaced` | Unidad sin posición factible, razón NO_FIT y contadores procesados/colocados. Un fallo técnico usa `optimization_failed`. |

`piece_placed` continúa siendo la prueba de aceptación, con posición, geometría
orientada, fuente y resolución. `group_completed` no basta para explicar por
sí solo qué pieza falló. `optimization_completed`/GET proveen el resultado final,
incluido SIN_SOLUCION y faltantes; no volver a ejecutar el algoritmo para verlo.

### RN-05 — Payload y experiencia acotados

- No transmitir eventos por celdas o posiciones candidatas individuales ni
  matrices densas completas. Las coordenadas de colocaciones aceptadas y los
  rangos compactos de una máscara autoritativa sí pertenecen al contrato.
- No repetir máscaras completas en cada evento. Compartir una referencia estable
  por máscara/contexto y reutilizar la representación ya obtenida; los eventos
  de evaluación llevan descriptores, no copias repetidas de sus celdas.
- Descriptores y `mask_ref` ligados a snapshot/resolución/ángulo; recuperar solo
  la máscara visible mediante contrato autenticado acotado, reutilizando rangos
  `spans_by_row`. URI/ventanas y retención según DG-01; schemas e implementación
  concretos de recuperación pendientes de T03.
- Los límites de HU-015 no se amplían para servir máscaras internas grandes.
  Si hace falta, ventanas/tiles o detalle visual reducido claramente rotulado;
  jamás cambiar por ello la máscara o resolución que usa el algoritmo.
- Acotar frecuencia, número y bytes mediante throttling, batching/agrupamiento
  o emisión de eventos significativos, según decida el PLAN con TA-037. Estos
  mecanismos limitan notificaciones sin introducir esperas ni operaciones
  geométricas para animar ni cambiar decisiones. Mantener orden/correlación de
  muestras reales e identificar que no son exhaustivas.
- No descartar colocaciones aceptadas, faltantes, errores ni terminales; cualquier
  agrupamiento conserva íntegros esos hechos y permite reconstruirlos en orden.
- La vista operativa muestra una evaluación relevante, no exige reproducir cada
  operación. Render por frame, canvas/viewport acotado y buffers sin historial
  infinito; el detalle técnico se abre a demanda.
- Distinguir procesadas de colocadas. No redefinir el porcentaje V1 ni forzar
  100 % de colocación para un resultado parcial.
- La máscara y geometría visualizadas deben corresponder a las utilizadas por
  la ejecución backend real para esa corrida, geometría original, orientación y
  resolución efectiva. La UI no presenta una rasterización independiente con
  reglas diferentes como si fuera la usada por el optimizador, ni usa un preview
  de otra corrida como sustituto.
  Si se muestran tiles o una representación reducida, deben derivarse de esa
  máscara y rotular sus límites; el detalle autoritativo permanece identificable.

### RN-06 — Contrapresión, desconexión y tiempos

Mantener cola acotada (actualmente tamaño 1), acknowledgement y cálculo fuera
de sesiones DB largas. La entrega visual no integra el tiempo computacional
del motor; los nuevos hitos de preparación deben definir su medición consistente.
No introducir pausas artificiales para animar ni alimentar decisiones desde la UI.

Hoy el cierre del transporte dispara aborto y cancelación cooperativa en hitos;
puede guardar FALLIDA/EXECUTION_INTERRUPTED y dejar pedidos EN_OPTIMIZACION para
reconciliación. No consume inventario. Si el resultado ya se guardó, no se pisa
por un fallo tardío de entrega. No afirmar cancelación inmediata por celda.

La UI debe diferenciar ocultar/pausar animación (conservar ejecución) de salir
y abortar conexión. Tras desconexión, consultar GET por ID/Location antes de
reintentar: no hay replay actual ni reanudación automática por abrir otro POST.
No normalizar pedidos ni inventar un endpoint de cancelación como parte implícita
de la visualización. TA-037 debe coordinar checkpoints durante preparación larga.

## 10. Criterios de aceptación

| CA | Criterio verificable | Tareas propuestas |
|---|---|---|
| CA-01 | Optimization es el único flujo principal visible para preparar y calcular. | T01/T04 |
| CA-02 | El operario no ejecuta una rasterización separada como prerrequisito. | T01 |
| CA-03 | Antes de iniciar FF/BF/WF se fijan resolución efectiva única, geometrías válidas, representaciones/máscaras base necesarias y configuración geométrica congelada; no se precalculan todas las orientaciones, posiciones, candidatos o layouts y se preserva la búsqueda lazy de FF. | T02 |
| CA-04 | Toda corrida usa una única resolución efectiva coherente en bases, orientaciones, materiales y placements, sin cambios durante la ejecución. | T02 |
| CA-05 | La resolución configurada/efectiva y la preparación respetan límites técnicos; error explícito si no caben, sin obligación de escoger automáticamente la mínima. | T02/T06 |
| CA-06 | Puede visualizarse la máscara autoritativa de la pieza durante preparación. | T03/T04 |
| CA-07 | Se identifica pedido, pieza y unidad actualmente procesados. | T03/T04 |
| CA-08 | Se visualiza la orientación relevante realmente evaluada, con muestreo identificado. | T03/T04 |
| CA-09 | Se observa cada colocación aceptada con su fuente y orientación. | T03/T04 |
| CA-10 | Se identifica cada pieza no colocada y su razón sin confundir fallo técnico. | T03/T05 |
| CA-11 | Activar, ocultar o reducir detalle visual no cambia las decisiones del algoritmo. | T02/T03/T06 |
| CA-12 | Desconectar/cerrar la visualización no modifica inventario; informa recuperación/estado real. | T03/T04/T06 |
| CA-13 | No se transmiten celdas/posiciones candidatas individuales ni máscaras completas repetidas por evento; frecuencia/payload/buffers acotados mediante throttling, batching o hitos significativos, preservando hechos críticos y decisiones algorítmicas. | T03/T06 |
| CA-14 | Se conserva determinismo para la misma instancia/configuración/política. | T02/T06 |
| CA-15 | FF conserva orden, placements, evaluación perezosa y salida temprana de búsqueda. | T02/T06 |
| CA-16 | WF conserva prioridad de retazos, colocación canónica, score posterior y desempates. | T02/T06 |
| CA-17 | La misma UI admite BF cuando su integración backend exista, sin motor ni UI duplicados. | T03/T04/T05 |
| CA-18 | Margen y separación se conservan en preparación, colocaciones y resultado. | T02/T06 |
| CA-19 | Retazos/planchas se identifican por material, espesor e identidad física. | T03/T04/T05 |
| CA-20 | Resultado muestra distribución, método, faltantes, métricas disponibles y residuales. | T05 |
| CA-21 | La simulación completa y su visualización no consumen ni reservan inventario. | T02/T06 |
| CA-22 | Confirmar sigue siendo acción explícita separada y autorizada sobre resultado persistido. | T05/T06 |
| CA-23 | V1 y rutas históricas HU-015 conservan compatibilidad durante la transición. | T01/T03/T06 |
| CA-24 | Responsive, teclado, foco y estados loading/error/desconexión/cancelación local están definidos y probados. | T04/T06 |
| CA-25 | Existen E2E del flujo unificado, incluidos parcial, recuperación y no consumo. | T06 |
| CA-26 | La máscara/geometría visualizada corresponde a geometría, resolución efectiva y orientación de la ejecución backend real; la UI no presenta una rasterización independiente con reglas diferentes como si fuera la del optimizador ni usa un preview ajeno. | T02/T03/T04/T06 |

Los 26 textos se conservan respecto de la aprobación. Su cumplimiento local se
traza en la matriz de evidencia de cierre, incluidas las condiciones de CA-17:
BF/WF HTTP siguen fuera de alcance. No se atribuye cumplimiento solo por la
existencia previa de HU-015/TA-019 ni por crear documentación.

## 11. Pruebas y evidencia previstas

- Contratos de preparación: máscaras base listas, resolución común y generación
  incremental de orientaciones/posiciones sin forzar búsqueda exhaustiva FF.
- Configuración geométrica congelada antes de buscar; cambios posteriores de
  ajustes o configuración vigente no alteran máscaras ni decisiones de la corrida.
- Unitarias de throttling/agrupamiento, serialización y compatibilidad de parsers;
  payload acotado y ausencia de eventos por posición candidata.
- Correspondencia entre máscara backend y visual: rangos, resolución y ángulo
  correctos, rechazo de referencias obsoletas y representación reducida rotulada.
- Componentes: máscara/ángulo actual, source real, loading, faltante, error,
  movimiento reducido, teclado y respuestas tardías de otra corrida/orientación.
- Integración: orden de eventos reales, backpressure, desconexión en preparación
  y búsqueda, snapshot/resultados recuperables, permisos y cero consumo.
- Regresiones FF/WF de dominio y cálculo con/sin perfil visual, mismos placements,
  faltantes y métricas; tiempos/timestamps se excluyen de igualdad geométrica.
- E2E unificado real: no cambiar a `hu015`, multipedido/multimaterial, rotación,
  retazo/fallback, SIN_SOLUCION, resultado/confirmación explícita y stock intacto
  antes de confirmar. Responsive y límite de detalle representativo.
- Evidencia de ejecución: `docs/evidence/sprint-02/HU-017/`, con base, comandos,
  resultados reales, capturas y medición de memoria/payload. T01/T02 conservan
  sus registros históricos y T03–T06 documentan la verificación final local.

## 12. Decisiones pendientes y dependencias

| Dependencia / GAP | Decisión requerida |
|---|---|
| TA-016 | Generación incremental compartida de orientaciones, orden/deduplicación, geometría/máscara coherentes y observación sin rotación propia de UI. |
| TA-018 / TA-019 | BF/WF integrados en dominio; instrumentación neutral del recorrido común, preservando sus políticas. La integración HTTP multimétodo sigue fuera de esta historia. |
| TA-021 | Comparación/orquestación de FF/BF/WF sobre la misma instancia, sin selección del ganador. Definición comunicada por el solicitante; coordinar contrato/ownership de resultados y eventos. HU-017 los consume visualmente y no decide el método ganador. |
| TA-037 | SPEC y guardrails integrados. Coordinar límites de resolución y recursos, máscaras base, generación bajo demanda, throttling y checkpoints; sin selección automática en HU-017. |
| Preparación base | Resuelta localmente mediante `PreparedRunGeometry` y orientaciones compartidas lazy; sin alterar políticas FF/BF/WF. |
| GAP-VECTORIAL | Decidir necesidad y alcance de validación final independiente; tarea separable, sin ID inventado ni garantía anticipada. |
| Contrato visual / máscaras | DG-01 Closed, B implementada/probada: negociación, URI, retención y tamaños acotados; sin persistencia de todos los intentos. |
| Configuración visible | Se muestra el snapshot efectivo al aceptar/recuperar la corrida. Sin nueva API pública de Configuration. |

## Historial de estado

| Fecha | Estado | Nota |
|---|---|---|
| 25/10/2026 | Draft | ID disponible localmente; propuesta funcional/compatibilidad basada en auditoría. Sin implementación ni aprobación automática. |
| 25/10/2026 | Draft | Revisión solicitada: máscaras base previas, orientaciones/posiciones lazy, resolución única sin mínimo automático, CA-26 de fidelidad visual y throttling explícito; negociación del contrato delegada al PLAN. |
| 25/10/2026 | Draft | Precisada invariancia previa a FF/BF/WF y congelación geométrica; fidelidad de máscara/geometría, eventos acotados sin máscaras repetidas y comparación de alternativas de streaming en el PLAN. |
| 25/10/2026 | Reviewed | Cierre documental autorizado por el solicitante. Revisión cruzada real pendiente; no Implemented ni Verified. TA-021 definida y HU-017 delimitada como consumidor visual sin selección del ganador. |
| 27/10/2026 | Reviewed | Base revalidada en `4bcf54d`; inicio local de T01 autorizado. Se conservan los 26 CA, las exclusiones y DG-01 abierta antes de T03. |
| 27/10/2026 | Reviewed | Primer incremento T01 implementado y validado localmente; [evidencia](../evidence/sprint-02/HU-017/t01-flujo-unificado.md). Sin cierre global ni publicación de HU-017. |
| 27/10/2026 | Reviewed | Núcleo T02 implementado en `1291d65`: bases previas, resolución/configuración inmutables y orientaciones compartidas lazy. 2270 backend y 34 E2E correctos; sin cierre global, publicación ni revisión humana atribuida. |
| 27/10/2026 | Reviewed | DG-01 Closed por elección expresa de B; contrato visual-v2 optativo documentado antes de T03. Sin código nuevo ni cambio de los 26 CA. |
| 28/10/2026 UTC | Verified — local | T01–T06 implementadas y verificadas: 2312 backend, ampliación API visual 12/12, 161 unitarias frontend, 506 componentes y 38 E2E; lint/build correctos. PostgreSQL temporal autorizado para HU-017. Sin publicación, integración ni revisión humana atribuida; CA/estimación intactos. |
