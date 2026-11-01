# SPEC-OPT-MULTIMOTOR-VISUAL — Ejecución y comparación visual de FF/BF/WF

## Información general

| Campo | Valor |
|---|---|
| Estado | **Implemented — verificación local completa; revisión cruzada y CI remoto pendientes** |
| Identificador documental | OPT-MULTIMOTOR-VISUAL; no atribuye un nuevo ID al backlog externo |
| PBI relacionados | HU-017, TA-021 y responsabilidades relacionadas de TA-025/TA-026/TA-038; los documentos disponibles se enlazan abajo |
| Autor y responsable funcional | Fabricio Melendez Quezada |
| Revisor | Andro Quispe; revisión cruzada pendiente de ejecución |
| Fecha | 31/10/2026, America/Lima |
| Rama | `feature/optimization-multimotor-visual` |
| Base | `integration/sprint-01`, `afd5f85f9dd1495e4237e1029555f7e56cd53f30` |
| PLAN | [PLAN-OPT-MULTIMOTOR-VISUAL.md](PLAN-OPT-MULTIMOTOR-VISUAL.md) |
| Autorización actual | Fabricio Melendez Quezada aprueba la SPEC y el PLAN y autoriza la implementación exclusivamente en esta rama, tras corregir autoría y revisión |

## 1. Objetivo

Permitir que una persona seleccione pedidos, ejecute **First Fit, Best Fit y
Worst Fit concurrentemente sobre las mismas condiciones**, observe su proceso,
compare sus resultados y elija explícitamente cuál utilizar. La aplicación no
elige automáticamente un ganador.

La experiencia muestra máscaras, orden de las piezas, rotaciones, colocaciones
y resultados con fases claras. Cada motor tiene su propia pestaña y existe una
cuarta pestaña de comparación. Después del cálculo siguen disponibles las
piezas solicitadas y las medidas originales que el sistema haya conservado.

### Base comprobada y relación con las fuentes

- [TA-021](SPEC-TA-021-comparacion-metodos.md) implementa comparación interna
  secuencial; excluye UI, selección del ganador y persistencia multimétodo.
- [HU-017](SPEC-HU-017-proceso-visual-optimizacion.md) y
  [DG-01](DECISION-HU-017-DG-01-streaming-visual.md) aportan preparación y eventos
  visuales reales. El transporte público y sus contratos actuales siguen siendo FF.
- [First Fit](SPEC-S1-optimization-first-fit.md),
  [Best Fit](SPEC-TA-018-best-fit.md), [Worst Fit](SPEC-TA-019-worst-fit.md),
  [rotación](SPEC-TA-016-rotacion-compartida.md) y
  [prioridad de retazos](SPEC-TA-020-retazo-priority.md) son capacidades existentes.
- [TA-037](SPEC-TA-037-control-carga-optimizador.md) aporta límites por ejecución.
  Tres motores concurrentes requieren además un presupuesto agregado.
- El snapshot actual reconstruye el resultado base FF: un round-trip de BF/WF
  pierde su identidad. Las nuevas comparaciones necesitan persistencia versionada.

Esta SPEC define el alcance de integración aprobado, ampliando las fronteras
anteriores sin reescribir retrospectivamente los cierres de esas tareas. Las
decisiones nuevas de API, persistencia y concurrencia del PLAN quedan autorizadas
para desarrollo; su aprobación no constituye implementación ni verificación.

## 2. Alcance

### Incluye

- Una operación comparativa con los tres motores, misma selección de pedidos,
  piezas, cantidades, stock capturado, configuración y reglas geométricas.
- Ejecución concurrente real, con resultados y estados independientes por motor.
- Preparación de máscaras, presentación del orden de piezas, evaluaciones de
  rotación y colocaciones reales, con transiciones visuales automáticas.
- Pestañas **First Fit**, **Best Fit**, **Worst Fit** y **Comparación**.
- Distribuciones y métricas por motor, inspección de piezas solicitadas,
  elección manual de un resultado y confirmación del resultado seleccionado.
- Persistencia, recuperación, permisos y controles de concurrencia necesarios
  para este ciclo, incluidos errores y liberación segura de pedidos del nuevo flujo.
- Pruebas de compatibilidad, integración completa, fidelidad visual y recursos.

### Fuera de alcance

- Cambiar las heurísticas, las fórmulas existentes de métricas, prioridad de
  retazos, geometría o paso angular operativo de 5°.
- Ranking automático, recomendaciones de ganador, ponderaciones o desempates
  entre motores. El nombre Best Fit no equivale a un ganador de la comparación.
- Cambiar el formulario de pedidos a centímetros: corresponde a la segunda rama
  acordada, `feature/orders-centimeters`, que no se crea en esta entrega.
- Nuevos CRUD generales de configuración/resultados, despliegues, promoción a
  `main`, cambios en datos reales o correcciones generales de inventario/RBAC.
- Infraestructura distribuida entre múltiples procesos web/dynos; el PLAN
  delimita una ejecución supervisada dentro del despliegue de un proceso web.
- Regenerar una historia inexistente de medidas originales o modificar resultados
  históricos para aparentar que se ejecutaron los tres motores.

## 3. Actor y precondiciones

**Actor:** persona autenticada que consulta, ejecuta, selecciona o confirma según
sus permisos. Mantener `optimization.view`, `optimization.execute` y
`optimization.confirm`. Se propone que seleccionar requiera execute; confirmar
continúa requiriendo confirm y una selección persistida válida.

**Precondiciones:** pedidos válidos en PENDIENTE, una configuración vigente
completa con paso de 5°, stock candidato validado y capacidad agregada disponible.
El inicio valida el lote completo y realiza una sola transición de pedidos.
Consultar pedidos o preparar una vista previa no inicia una ejecución.

## 4. Entradas y datos

| Dato | Contenido y regla |
|---|---|
| Solicitud | IDs de pedidos distintos; conjunto fijo de métodos FF/BF/WF en este flujo |
| Identidad comparativa | ID de comparación y exactamente una ejecución identificada por cada método |
| Snapshot común | Pedidos/piezas, cantidades, material/espesor, geometrías y medidas persistidas originales, configuración y stock físico candidato con su orden estable |
| Resultado por método | Identidad explícita, estado, completitud, colocaciones/faltantes, materiales usados, métricas, duración y error público si corresponde |
| Selección | ID de ejecución elegida y versión de la comparación; ninguna selección al iniciar |
| Eventos | Comparación, ejecución/método, secuencia, fase y datos de avance correlacionados |
| Medidas solicitadas | Valores del snapshot del pedido; nunca sustituirlos por dimensiones de la pieza ya rotada |

Unidades canónicas: mm, mm² y grados según los contratos actuales. Esta primera
rama conserva esas unidades y las rotula explícitamente. La futura rama de cm
debe definir conversión y unidades de presentación sin multiplicar nuevamente
los datos existentes. No se denomina «medida ingresada» a una medida derivada.

En polígonos se conservan los vértices enviados y los metadatos de dimensiones
que realmente existan. Longitudes/ángulos calculados a partir de esos vértices
se etiquetan como calculados; no se afirma que fueron digitados si no se guardó
ese dato. Ausencia de un metadato histórico se informa sin inventarlo.

## 5. Reglas de negocio

- **RN-01 — Entrada equivalente:** capturar una vez las condiciones comunes.
  Cada motor recibe un estado lógico equivalente e independiente. No releer
  stock por método ni pasarle el layout final de otro.
- **RN-02 — Concurrencia:** los tres cálculos se despachan como un mismo trabajo
  y pueden progresar en paralelo. Tres llamadas secuenciales o tres pestañas que
  muestran un mismo FF no satisfacen el requisito. No se exige igualdad de
  timestamps de arranque; sí solapamiento demostrable de ejecuciones.
- **RN-03 — Políticas existentes:** conservar preparación, desempates, primer
  placement por fuente, salida temprana FF y selectores BF/WF. La observación no
  evalúa candidatos adicionales para producir animaciones.
- **RN-04 — Simulación sin consumo:** calcular, cambiar de pestaña, comparar y
  seleccionar no consumen ni reservan inventario. Solo la confirmación aplica
  el resultado elegido, una vez y de manera transaccional.
- **RN-05 — Identidad durable:** conservar método y ejecución en eventos,
  máscaras, resultados y recuperación. BF/WF no pueden recuperarse como FF.
  Prohibido deducir identidad del índice de una pestaña o arreglo.
- **RN-06 — Selección humana:** no seleccionar FF por defecto, ni al primero que
  termine, ni al de menor tiempo/merma. Comparación presenta métricas con iguales
  fórmulas, unidades y entrada, sin calificar por sí misma a un ganador.
- **RN-07 — Elegibilidad:** permitir elegir para aplicar únicamente un resultado
  completo, terminal y guardado de esa comparación. Esperar a que los tres
  motores estén terminales para habilitar la elección final. Si alguno falla,
  mostrar comparación incompleta y resultados disponibles; un éxito completo
  puede elegirse explícitamente, sin presentar el conjunto como tres éxitos.
- **RN-08 — Confirmación:** exige selección vigente, permiso y revalidación de
  pedidos/stock. Aplica únicamente colocaciones, consumo, movimientos y retazos
  de la ejecución elegida. Dos confirmaciones concurrentes no duplican efectos.
- **RN-09 — Selección versionada:** puede cambiarse antes de confirmar. Selección
  y confirmación concurrentes usan bloqueo/versionado; una selección obsoleta
  responde conflicto. Después de confirmar no puede reemplazarse el resultado.
- **RN-10 — Datos solicitados:** mantener accesibles pedido, pieza, forma,
  cantidad, material/espesor y medidas originales junto a las métricas y después
  de recuperar una comparación. Distinguir unidades pedidas, colocadas y faltantes.
- **RN-11 — Proceso real:** todas las máscaras y orientaciones corresponden a
  hechos del backend. Informar que las orientaciones son muestras cuando se
  limite la telemetría. La UI no fabrica porcentajes, evaluaciones o duración.
- **RN-12 — Ordenamiento visible:** mostrar primero las máscaras y después el
  orden real de procesamiento mediante fases visuales. El orden puede haberse
  calculado antes; el evento informa el orden disponible, no simula que el motor
  sigue ordenando ni modifica el algoritmo para adaptarlo a una animación.
- **RN-13 — Transiciones:** cada pestaña avanza automáticamente según los hechos
  de su ejecución. El usuario puede inspeccionar fases anteriores y cambiar de
  pestaña sin reiniciar cálculos. No cambiar automáticamente la pestaña elegida.
  Si el cálculo es muy rápido, conservar fases completadas consultables, sin
  introducir esperas artificiales que aparenten trabajo todavía en curso.
- **RN-14 — Rotaciones:** mostrar contorno/máscara orientados y colocación con
  el ángulo realmente evaluado o elegido. No aplicar dos veces el giro. Pausar
  la vista o reducir animaciones no detiene la recepción ni el cálculo.
- **RN-15 — Recursos:** admitir una comparación solo si pueden ejecutarse sus
  tres motores dentro de límites agregados. Rechazar antes de mutar pedidos si
  no hay capacidad; no degradar silenciosamente a ejecución secuencial.
- **RN-16 — Recuperación:** una desconexión de observación no es NO_FIT. Recuperar
  estados/resultados desde el servidor sin iniciar otro cálculo. La liberación
  de pedidos exige comprobar que los trabajadores terminaron y que no hubo
  confirmación; preservar toda historia y realizar la transición atómicamente.

## 6. Flujo principal

1. Seleccionar pedidos y consultar el resumen de piezas/medidas sin cambiar estados.
2. Iniciar una comparación. El backend valida y congela la entrada, obtiene
   capacidad para tres motores, crea sus identidades y acepta el lote una sola vez.
3. Lanzar los tres cálculos concurrentemente. Las pestañas muestran estado y
   motor identificados, aunque el usuario observe solo una.
4. En cada ejecución, mostrar las máscaras base y el fin real de su preparación.
5. Avanzar automáticamente al orden real de las unidades; luego mostrar las
   evaluaciones representativas de rotación y las colocaciones progresivas.
   Ordenamiento y acomodo sobre planchas se presentan como conceptos diferentes.
6. Incorporar el resultado y las métricas de cada motor cuando se hayan guardado.
   Un motor puede finalizar antes que otro sin reemplazar ni bloquear su pestaña.
7. En Comparación, mostrar FF/BF/WF, estados, distribuciones y métricas comunes,
   con acceso al detalle de piezas solicitadas y sus medidas originales.
8. Con los tres terminales, la persona elige un resultado elegible. Persistir la
   elección y mostrarla. Seleccionar no equivale a confirmar el corte.
9. Al confirmar, revalidar y aplicar solo la ejecución elegida. El resto se
   conserva para comparación histórica, sin consumos adicionales.
10. Al volver a abrir el trabajo, recuperar las tres ejecuciones, la elección,
    confirmación y medidas solicitadas; no recalcular para dibujar un resultado.

## 7. Flujos alternativos y errores

| Situación | Comportamiento requerido |
|---|---|
| Pedido/configuración inválidos o capacidad insuficiente | Rechazo explícito, sin aceptar parcialmente el lote ni cambiar stock/pedidos |
| Sin solución en un motor | Resultado parcial identificable; conservar faltantes y métricas disponibles; no habilitar su confirmación |
| Fallo/timeout de un motor | Marcar ese motor fallido, conservar éxitos de los otros y distinguir comparación incompleta; no inventar un resultado |
| Ningún motor produce solución completa | Sin elección confirmable; cierre y liberación segura de pedidos cuando hayan terminado todos; no retenerlos por limpiar solo estado UI |
| Interrupción del proceso o resultado no persistido | Mostrar situación reconciliable; no dar por confirmado/guardado lo que no está en BD; recuperación controlada sin trabajadores vivos |
| Desconexión, recarga o cambio de pestaña | Recuperar estado autoritativo por identidad, evitar POST duplicado y no reiniciar los motores |
| Stock cambia antes de confirmar | Conflicto con rollback total; conservar comparación/elección y ofrecer salida de reconciliación segura para iniciar otro trabajo |
| Selección o confirmación concurrentes | Validar versión y pertenencia; una elección ajena/obsoleta no se aplica |
| Máscara expirada o presupuesto visual agotado | Mensaje explícito; resultado persistido disponible; no sustituir silenciosamente una máscara por otra |
| Permiso revocado o sesión vencida | Rechazo backend y respuesta UI apropiada; ningún control visual sustituye la autorización |

Reintentar tras liberar un lote crea una nueva comparación y un nuevo snapshot,
sin sobrescribir los resultados anteriores. No se autoriza una reparación masiva
de pedidos históricos retenidos de otros flujos.

## 8. Criterios de aceptación

| ID | Comprobación |
|---|---|
| CA-01 | Una selección produce exactamente una comparación y una ejecución FF/BF/WF, con un único cambio inicial del lote |
| CA-02 | Los tres reciben mismos pedidos, cantidades, geometrías, configuración y snapshot/ranking de stock; sus estados son independientes |
| CA-03 | Una prueba con barrera demuestra ejecución concurrente real; no se aceptan tres invocaciones secuenciales |
| CA-04 | Existen las cuatro pestañas y cada una conserva el resultado y progreso de su identidad correcta |
| CA-05 | Cambiar de pestaña no genera otra aceptación, reinicio ni consumo de stock |
| CA-06 | Los tres motores aportan hechos reales de preparación y máscaras; las máscaras están ligadas a su ejecución, resolución y orientación |
| CA-07 | La UI muestra máscaras y avanza al orden real de piezas mediante eventos/fases verificables; no simula duración de ordenamiento |
| CA-08 | Se visualizan rotaciones reales, ángulo y material/posición, sin doble transformación y con aviso de muestreo |
| CA-09 | Colocaciones, faltantes y progreso son coherentes por motor aunque los eventos se intercalen o terminen en otro orden |
| CA-10 | Nombre del motor y fase permanecen identificados durante el proceso y en el resultado |
| CA-11 | Cada resultado completo/parcial/fallido es independiente y sus métricas se identifican con el mismo motor |
| CA-12 | Comparación muestra tres filas/resultados y métricas con unidades y significado equivalentes; fallos no figuran como valores cero |
| CA-13 | No hay ganador ni elección predeterminados; la persona puede elegir un resultado completo guardado cuando los tres sean terminales |
| CA-14 | Selección pertenece a la comparación, queda versionada y se recupera; cambiarla antes de confirmar no altera stock |
| CA-15 | Confirmar aplica una sola vez y exclusivamente el elegido, incluso con solicitudes concurrentes o respuesta ambigua |
| CA-16 | Se recuperan FF/BF/WF con su identidad, configuración, colocaciones, métricas, faltantes y elección intactos |
| CA-17 | Se consultan piezas, cantidades y medidas originales después de las métricas y tras recarga, sin usar la geometría rotada como original |
| CA-18 | Rectángulos, círculos y polígonos muestran datos persistidos y unidades explícitas; valores derivados se distinguen de ingresados |
| CA-19 | Capturas y pruebas responsive/teclado cubren las cuatro pestañas, fases y comparación; movimiento reducido conserva funcionalidad |
| CA-20 | Tiempo/memoria/colas/concurrencia tienen límites agregados medidos; un rechazo previo conserva pedidos e inventario |
| CA-21 | Fallo, cancelación técnica, desconexión y reinicio no mezclan motores ni presentan trabajos incompletos como tres éxitos |
| CA-22 | Ninguna solución o abandono reconciliado libera el lote del nuevo flujo con trabajadores terminados y sin aplicar stock |
| CA-23 | Un conflicto de stock no consume parcialmente y permite una salida segura a nuevo trabajo conservando la historia |
| CA-24 | RBAC protege consulta, ejecución, selección y confirmación; selección ajena o versión obsoleta se rechaza |
| CA-25 | Contratos FF V1/visual-v2 y resultados históricos conservan comportamiento; no se reetiquetan ni se eliminan pruebas para lograr verde |
| CA-26 | Evidencia E2E real demuestra máscaras → orden visible → rotaciones/colocaciones → tres resultados → elección → confirmación y recuperación |

## 9. Impacto técnico

**Módulos:** Optimization coordina el ciclo; Orders aporta piezas y estados;
Inventory aporta stock y confirma los efectos a través de contratos existentes;
Authentication/RBAC mantiene la autorización. No copiar lógica heurística a UI.

**API:** recurso comparativo `comparison-v1` con aceptación, consulta,
observación, selección versionada, confirmación idempotente y liberación.
Las rutas FF históricas se preservan; el flujo principal usa `/comparisons`.
Consultar la [guía de contrato](../contracts/optimization/comparison-v1.md).

**BD/migración:** migración aditiva `s2cmp01a1b2c`, con clave, snapshot común y
versión de comparación en el agregado existente; mantiene las tablas de
ejecución por método. El codec de resultado V2 conserva FF/BF/WF y sigue leyendo
FF V1 histórico. Las pruebas verifican migración, recuperación y bloqueo del
downgrade cuando existe historia comparativa; no se migró la base remota.

**UI:** un controlador por comparación, estados por motor, pestañas accesibles,
fase visual/inspección separadas del cálculo, comparación y detalle de solicitud.

## 10. Pruebas previstas

Pruebas unitarias de codecs y estados; dominio con/sin observación; concurrencia
de trabajadores; API/NDJSON y recuperación; migraciones y transacciones en
PostgreSQL temporal; componentes; E2E de escritorio/móvil con datos sintéticos.
Incluir orden intercalado de eventos, CPU/memoria agregadas, fallos de persistencia,
confirmaciones concurrentes y regresiones FF. Lint/build son comprobaciones
adicionales, no sustitutos del recorrido funcional.

## 11. Evidencias requeridas

- Matriz CA-01–26 con fuente, comando, entorno y resultado real.
- Trazas que demuestren solapamiento de los tres motores y snapshot equivalente.
- Capturas por fase/motor, rotaciones, cuatro pestañas, comparación y detalle de
  medidas originales; incluir responsive y movimiento reducido.
- Resultados BD antes/después de simular, seleccionar, confirmar y recuperar;
  demostrar que solo el elegido consume stock y que BF/WF no se convierten en FF.
- Medición agregada de recursos, suites relevantes y CI del commit implementado.

La auditoría de la base obtuvo 2364 pruebas backend, 175 unitarias frontend y
506 de componentes aprobadas; E2E escritorio 57/57 y móvil aislado 56/57, con
fallo del registro de retazo personalizado. El CI de `afd5f85` había aprobado
114 E2E. Son antecedentes de la base, no evidencia de esta implementación.
Estos antecedentes no satisfacen por sí mismos ningún CA de la nueva integración.
La autorización de desarrollo por sí sola no declara criterios cumplidos. El
cierre posterior de esta rama registra 2453 pruebas backend, 175 unitarias
frontend, 514 de componentes y 120 E2E aprobadas, además de 8 pruebas enfocadas
de avance automático/contrato. Consultar la [matriz de los 26 CA](../evidence/sprint-02/OPT-MULTIMOTOR-VISUAL/README.md)
para fuentes, comandos, capturas y límites. Revisión cruzada y CI remoto pendientes.

## Historial de estado

| Fecha | Estado | Registro |
|---|---|---|
| 31/10/2026 | Draft | SPEC preparada por solicitud expresa; pendiente revisión y aprobación. Sin implementación ni cierre de tareas externas |
| 31/10/2026 | Reviewed | Fabricio Melendez Quezada confirma autoría, asigna revisión a Andro Quispe, aprueba SPEC/PLAN y autoriza iniciar desarrollo en `feature/optimization-multimotor-visual`. Revisión cruzada y verificación funcional pendientes |

| 31/10/2026 | Implemented | T00–T07 desarrolladas y verificadas localmente: tres motores supervisados, API/recuperación, cuatro pestañas, fases/giros, solicitud original, selección y confirmación exclusiva. Evidencia de 2453 backend, 175 unitarias frontend, 514 componentes y 120 E2E aprobadas; 26 CA trazados. Revisión de Andro Quispe y CI remoto pendientes; sin PR/merge/despliegue |
