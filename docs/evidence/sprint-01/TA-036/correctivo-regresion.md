# TA-036 — correctivo de regresión previo a T06

Validación local completada el 2026-10-13 en `TA036-saneamiento-worktree`, rama
`feature/TA-036-saneamiento-funcional`. Inicio limpio en `58911a6`; comparación
contra `origin/integration/sprint-01` (`b7a0175`). No se ejecuta T06, push,
integración de ramas, Staging ni conexiones a servicios externos. PostgreSQL
utilizado por las pruebas es temporal, aislado y de loopback.

## Causa y conteos reproducibles

Los mismos comandos son `npm.cmd run test:unit` (Node: `tests/unit/*.test.js`)
y `npm.cmd run test:component` (Vitest: `vitest run`). No cambian package.json,
configuración Vitest, patrones de descubrimiento ni exclusiones. Ninguno de
los tres archivos auditados se eliminó o renombró: se sustituyó su contenido.
No hay skips nuevos en unit/component. El diff previo sí tiene un `test.skip`
condicional de Playwright para una mutación de recurso compartido entre
viewports; pertenece a E2E y no explica ninguno de estos conteos.

| Suite / archivo | Base | Antes del correctivo | Final |
| --- | ---: | ---: | ---: |
| Unit: geometryScaling.test.js | 38 | 23 | 40 |
| Unit: resto | 63 | 63 | 63 |
| **Unit total** | **101** | **86** | **103** |
| Component: CustomPieceEditor.test.jsx | 28 | 16 | 26 |
| Component: InventoryPage.test.jsx | 8 | 4 | 7 |
| Component: Hu014Inventory.test.jsx | 27 | 32 | 32 |
| Component: RegistrarRetazoGeometry.test.jsx | 0 | 3 | 3 |
| Component: resto | 143 | 143 | 143 |
| **Component total** | **206** | **198** | **211** |

- **101→86:** la reescritura de geometryScaling sustituyó 38 casos por 23.
  Retiró el resolvedor de lados independientes, pero también límites del
  preview, casos numéricos y guardas todavía vigentes. El correctivo añade
  17 casos y refuerza aserciones de los existentes. Algunos antiguos bucles
  parametrizados se comprueban juntos; el total final no pretende reproducir
  la agrupación anterior.
- **206→198:** CustomPieceEditor perdió 12 casos al sustituir dimensiones
  independientes por escala uniforme; se perdieron también selección visual,
  entradas pequeñas y limpieza del estado geométrico. InventoryPage perdió
  cuatro casos netos: salieron cinco ejecuciones antiguas (cuatro declaraciones,
  una parametrizada en dos recursos) y entró una que verifica ausencia de
  toggles. Se perdió protección HTTP/cancelación/refresco junto con los botones
  obsoletos. HU014 añadió cinco y el registro de retazo tres: -12-4+5+3=-8.
- El correctivo añade diez casos del editor y tres de InventoryPage. El delta
  final contra base es +2 unit y +5 component: editor -2, InventoryPage -1,
  HU014 +5 y registro de retazo +3. No se recuperan números mediante duplicados
  ni reinstalando contratos obsoletos.

## Matriz de geometría

Origen de todas las filas: versión base de
`frontend/tests/unit/geometryScaling.test.js`. Los equivalentes están en ese
mismo archivo final; los nombres abreviados corresponden a prefijos únicos de
tests. “Mixto” distingue las aserciones vigentes de la premisa obsoleta.

| Test anterior | Clasificación | Equivalente actual | Motivo |
| --- | --- | --- | --- |
| graphical segment length uses Euclidean distance, independent of translation | Vigente | `equal lengths cannot determine shape`, `scale preserves shape`, `rotated/translated canonical sketch` | Longitudes euclídeas y traslación se verifican desde los vértices, incluido triángulo 3-4-5. |
| segment IDs and indices preserve drawing order, including the closing side | Vigente | `segment IDs and indices include the closing edge`; `partial measurements remain provisional` | Conserva IDs, orden, arista de cierre y escala derivada; rechaza IDs/orden corruptos. |
| no real measure means no physical scale and no vertices_mm | Vigente | `partial measurements remain provisional`; `clearing all measurements` | Unscaled no produce vértices físicos. |
| a single measurement supplies the provisional scale without filling blank inputs | Vigente en función pura | `partial measurements remain provisional` | Escala 2, flags y longitudes derivadas; la función no muta blancos. La UI ahora completa los demás lados proporcionalmente. |
| odd median is robust to an outlier and even median averages central scales | Mixto | `odd and even subsets of canonical measurements`; `inconsistent independent lengths` | Subconjuntos consistentes dan la misma escala. Se retira la expectativa de cambiar una forma usando medidas incompatibles/outliers. |
| complete model uses only entered lengths | Obsoleto | `equal lengths cannot determine shape`; `partial measurements remain provisional` | Los lados solos no definen el contorno; el resultado completo transforma los vértices canónicos. |
| known rectangle preserves reference directions and has origin at its first vertex | Vigente | `partial measurements remain provisional`; `rotated/translated canonical sketch` | Coordenadas esperadas, orientación y origen conservados. |
| three sides reconstruct a known 3-4-5 triangle | Mixto | `scale preserves shape, vertex order and angle sum in either winding` | Se conserva el triángulo canónico y su escala; se retira inferencia exclusivamente desde tres lados. |
| editing one side changes geometry, closes the chain and keeps all other lengths | Obsoleto | Editor: `editar otro lado reescala proporcionalmente` | El contrato actual escala todos los vértices; mantener los otros lados independientes cambiaría la forma. |
| reference orientation and vertex order survive a rotated, translated sketch | Vigente | `rotated/translated canonical sketch` | Comprueba coordenadas exactas ordenadas y ángulos. |
| five different real lengths reconstruct deterministically | Obsoleto | `equal lengths cannot determine shape`; `inconsistent independent lengths` | No hay resolvedor de polígono arbitrario a partir de cinco longitudes. |
| concave sketches are dimensioned without T03 validation | Vigente | `concave angles are derived with reflex vertex; validation remains separate` | La conversión pura escala el contorno cóncavo; el validador lo rechaza sin repararlo. |
| six or more segments satisfy each target length | Mixto | `six or more vertices retain their canonical shape` | Casos 6/8/12 conservados, usando lados derivados del contorno; se retiran objetivos independientes arbitrarios. |
| a collinear reference can escape the rank-deficient initial directions | Obsoleto | `thin non-degenerate canonical triangle`; `degenerate geometry` | Una línea no puede convertirse artificialmente en triángulo por asignarle lados. |
| invalid length (11 valores: 0, -1, NaN, Infinity, -Infinity, abc, vacío, espacio, null, undefined, true) | Vigente | Siete `invalid length … cannot yield a polygon` y `remaining non-finite and malformed length inputs` | Todos los valores anteriores siguen comprobados, cuatro agrupados en un caso. |
| strict polygon inequality rejects equality and a side longer than all others | Obsoleto como resolvedor | `inconsistent independent lengths` | La entrada incompatible se rechaza con shape-mismatch; no se busca una forma alternativa. |
| inconsistent provisional lengths cannot claim a complete preview | Vigente | `inconsistent independent lengths` | Estado error, shape-mismatch y vertices_mm null para medidas parciales incompatibles. |
| incomplete native numeric input is an error, not an unmeasured estimate | Vigente | `native badInput is an error` | Flag nativo con valor vacío o valor numérico anterior no puede emitir geometría. |
| positive decimals below 0.01 are accepted | Vigente | `positive physical lengths below 0.01`; editor `longitud 0.001 válida` | 0.005, 0.001 y 0.000001 en escala pura; 0.001 y lado derivado 0.0005 en UI real. |
| near-degenerate feasible lengths can still close | Mixto | `thin non-degenerate canonical triangle` | Triángulo canónico estrecho válido conserva forma y ángulos; colineal sigue inválido. No se reconstruye desde desigualdad de lados. |
| missing edges, repeated adjacent vertices and non-finite drawings fail explicitly | Vigente | `malformed/repeated/non-finite sketch vertices`; `segment IDs and indices`; `invalid scale, numeric overflow` | Rechaza vértices insuficientes/repetidos/no finitos, cantidad incorrecta de aristas y orden inválido. |
| overflowing provisional scale fails without emitting invalid vertices | Vigente | `overflow of provisional scale fails` | Sketch 1e-300 y medida 1e300: numeric-range y vertices_mm null. |
| all geometry operations leave frozen inputs unchanged | Vigente | `dimensional pipeline leaves frozen sketch and segment inputs`; `frozen coordinates remain unchanged` | Congela entradas de la conversión y del preview; comprueba bbox e inmutabilidad. |
| preview preserves 200:5000 at desktop and mobile sizes | Vigente | `canonical 200:5000 polygon preserves angles` | Tres viewports, límites, proporción, inmutabilidad y ángulos. |
| preview preserves 5000:200 at desktop and mobile sizes | Vigente | `canonical 5000:200 polygon preserves angles` | Tres viewports y extremos del eje horizontal, con geometría canónica. |
| preview preserves 1000:500 at desktop and mobile sizes | Vigente | `frozen coordinates remain unchanged through scaling and responsive previews` | Misma relación 2:1, centrado y márgenes en los mismos tres viewports. |
| preview rejects invalid bounds and handles non-origin and one-axis extents | Vigente | `invalid scale, numeric overflow`; `preview rejects invalid and non-finite viewport`; `preview rejects negative/non-finite padding`; `one-axis preview extents` | Dimensiones inválidas en ambos ejes, padding negativo/no finito/excesivo, entradas inválidas, extensión horizontal/vertical centrada sin mutar. |
| clearing a completed length returns to provisional; clearing all removes physical scale | Vigente | `clearing all measurements removes physical scale`; `partial measurements remain provisional` | Función pura conserva provisional al borrar uno; al borrar todos retira vértices físicos. |

El correctivo conserva los casos TA-036 de valores finitos, degenerados,
ángulos reflejos y dos formas con iguales lados pero distinta disposición.
La invariancia angular se exige a la transformación uniforme, no a cualquier
transformación geométrica imaginable.

## Matriz de CustomPieceEditor

Origen: versión base de
`frontend/src/features/orders/__tests__/CustomPieceEditor.test.jsx`. Los
equivalentes se localizan por título en el archivo final.

| Test anterior | Clasificación | Equivalente actual | Motivo |
| --- | --- | --- | --- |
| T01-C01…C05, T01-C06 (abierto/cerrado) | Vigentes, conservados | Mismos IDs | Inicio, dibujo, cierre y controles no se retiran; helper inicial refuerza estado pendiente. |
| T02-C01: campos vacíos y sin escala | Vigente | `cierre identifica todos los campos requeridos` | Required, step any, progreso, guardado bloqueado y selección inicial en ambos SVG. |
| T02-C02: una medida deja cuatro campos vacíos pendientes | Obsoleto en UI | `una longitud fija escala y deriva todos los lados y ángulos` | Una medida válida escala el contorno y completa los lados derivados. Función pura parcial se prueba por separado. |
| T02-C03: selección S1→S3→S5 sincroniza ambos SVG | Vigente | `selección y hover conservan arista y etiqueta sincronizadas`; `selección por foco directo` | Aserciones sobre líneas y textos activos de ambos SVG, aria-pressed y foco, antes/después de medir. Hover no cambia selección en el contrato actual. |
| T02-C04: editar una medida conserva otros campos independientes | Mixto | `editar otro lado reescala proporcionalmente` | Se conservan contorno/ángulos/proporción; los otros campos se derivan de la nueva escala. |
| T02-C05: dimensiones completas sin registro mantienen Agregar disabled | Vigente | `editar otro lado reescala proporcionalmente`; `geometría completa no autoriza guardar sin material` | Valida falta de callback de registro y headerReady false, con explicación accesible. |
| T02-C06: 1000/100/100/100/100 informa imposibilidad | Obsoleto | Unit: `inconsistent independent lengths`; editor de escala uniforme | La UI ya no ofrece cinco objetivos independientes incompatibles. No se inventa flujo inaccesible. |
| T02-C07 (0 y -1) | Vigente | `medida %s inválida bloquea guardar` | Ambos valores, mensaje accesible y ausencia de ángulos. |
| T02-C08: positivo menor que 0.01 | Vigente | `longitud 0.001 válida produce vértices pequeños` | Escritura con userEvent, validación y payload exacto de vértices. |
| T02-C09: borrar uno/todos | Vigente adaptado | `borrar una longitud invalida el guardado`; `borrar todas las medidas retira escala` | No persiste resultado válido anterior ni permite guardar incompleto. |
| T02-C10: deshacer después de medir y recerrar | Vigente | `deshacer una figura dimensionada invalida el resultado` | Retira preview, ángulos y éxito; recierre crea campos vacíos y selección S1. |
| T02-C11: reiniciar después de medir | Vigente | `reiniciar después de medir elimina escala y selección` | Nuevo dibujo sin medidas/selección/ángulos residuales. |
| T02-C12: cierre/selección por teclado | Vigente | `cierre y selección por teclado conservan foco` | Ruta real Tab/Enter para cerrar y seleccionar, sin sustituir navegación por focus programático. |
| T03-C01: pendiente antes de cerrar y con dimensiones estimadas | Mixto | Helper `expectInitial`; `cierre identifica todos los campos requeridos` | Pendiente inicial/unscaled conservado; pendiente tras una medida válida es obsoleto porque deriva el resto. |
| T03-C02: éxito convexo sin registro | Vigente | `editar otro lado reescala proporcionalmente`; `geometría completa no autoriza guardar sin material` | Estado válido no basta sin contexto de registro. |
| T03-C03: contorno cóncavo rechazado | Vigente | `contorno cóncavo sigue rechazado después de cambiar escala` | Rechazo antes y después de reescalar. |
| T03-C04: bow-tie anuncia autointersección | Vigente | `contorno autointersección sigue rechazado después de cambiar escala` | Mensaje específico y guardado bloqueado. |
| T03-C05: editar un lado cambia concavidad→cruce→concavidad | Obsoleto | `contorno cóncavo sigue rechazado después de cambiar escala` | Escala uniforme no cambia concavidad ni disposición. |
| T03-C06: invalidar/borrar y corregir recalcula | Vigente | `invalidar y corregir una dimensión retira y recalcula la validación`; `borrar una longitud invalida el guardado` | Secuencia válida→0→válida→vacía→válida sin éxito obsoleto. |
| T03-C07 (deshacer y reiniciar tras éxito) | Vigente | `deshacer una figura dimensionada`; `reiniciar después de medir` | Ambos controles retiran validación y geometría guardable. |

Se conserva el rechazo TA-036 de colineales y se añade rechazo visual de
vértices consecutivos repetidos. La implementación ya satisfacía estas
capacidades; no fue necesario cambiar producción frontend.

## Matriz de InventoryPage

Origen: versión base de
`frontend/src/features/inventory/__tests__/InventoryPage.test.jsx`.

| Test anterior | Clasificación | Equivalente actual | Motivo |
| --- | --- | --- | --- |
| 403 muestra permisos, conserva sesión y no refresca (al desactivar) | Mixto | `403 al editar conserva sesión y borrador` | Se conserva HTTP 403 real del flujo, borrador, token, sesión y ausencia de refresh; se retira el botón desactivar. |
| cancelar desactivación no envía PATCH ni cambia estado | Mixto | `cancelar la revisión de baja parcial no envía POST` | Cancelación/foco/no mutación vigentes en nueva confirmación de baja. |
| activar material inactivo mediante PATCH inmediato | Obsoleto | `solo ofrece historial, edición y baja, sin toggles de estado` | Activar manual no vuelve a la UI; los servicios/API internos de estado permanecen. |
| confirmar desactivación actualiza recurso y listado (plancha y retazo) | Mixto, dos ejecuciones | `editar cantidad usa PATCH y refresca el saldo visible`; HU014 baja parcial/retazo | Se preserva refresco tras mutación usando acciones actuales; no se restaura desactivación manual. |
| 422 conserva formulario; loading/vacío; fallo de red | Vigentes, conservados | Mismos títulos | Los tres casos existentes permanecen. |

En Hu014Inventory permanecen sin cambios las regresiones TA-036 de baja 1 de
10→9 incluso si falla refresh, cantidad inválida, historial, retazo dado de
baja detrás del disponible y sin cantidad editable. Tampoco se modifica la
cobertura de reutilización del editor y payload de retazo.

## cantidad_afectada: escrituras y compatibilidad histórica

Revisión de todas las referencias en `backend/app`: la única construcción
persistente de MovimientoInventario está en el escritor común del repositorio.
Lecturas/DTOs permiten None para historial. No hay escritor adicional de bajas
ni escritor de consumo de Optimization implementado en esta base.

| Capa | Garantía |
| --- | --- |
| Request / endpoint plancha | BajaPlanchaRequest exige int estricto >0, campo obligatorio; router pasa el valor. Ausente, NULL, booleano, fracción y no positivo: 422. |
| Request / endpoint retazo | BajaManualRequest prohíbe campos extra; no se acepta cantidad editable. Router crea comando sin cantidad. |
| Dominio BajaManual | Cualquier cantidad explícita debe ser entero estricto positivo; None permite el comando unitario de retazo, no autoriza persistir None. |
| Servicio plancha | Lock, existencia/disponibilidad, `_integer` positivo y límite de saldo antes del escritor; None no llega a insert. |
| Servicio retazo | Solo comando None/1; repositorio unitario asigna 1 explícitamente. |
| Repositorio común (correctivo) | Rechaza None, bool, fracción/string y <=0 antes de insertar; para retazo rechaza distinto de 1. Protege también llamadas internas que omitan servicio. |
| DB / ORM | Integer nullable; CHECK positivo si conocido y CHECK unitario de retazo si conocido. No decide si una fila es histórica por su fecha de inserción. |

La SPEC 6.3/6.4 y CA-12 exige cantidad válida en nuevas bajas de aplicación y
preservación del histórico desconocido. No exige que SQL directo diferencie
filas nuevas de antiguas. Se documenta explícitamente: **SQL directo aún puede
insertar NULL**, aunque su admisión en el esquema tiene el propósito de
compatibilidad histórica. No se afirma una garantía temporal inexistente.
No se crean triggers, columnas legacy ni fechas/cutoffs.

Migración **ta036a1b2c3d**, padre **fa014e1a2b3c**, sin modificación. Historial
desconocido de plancha conserva NULL; bajas manuales de retazo admiten backfill
1 por representar unidades concretas. No default que invente cantidades.
Upgrade y CHECK se verifican en PostgreSQL; downgrade bloquea atómicamente
pérdida de cantidades/múltiples bajas con lock y permite ciclo vacío seguro.
Solo se amplían tests de migración, no revisiones históricas ni esquema.

Pruebas añadidas: dominio (seis entradas inválidas), escritor plancha real
(seis entradas inválidas sin inserción ni cambio de saldo), escritor común de
retazo no unitario, servicio real (None rechazado en plancha y asignación 1 en
retazo), HTTP autenticado con servicio/repositorio reales y PostgreSQL aislado.
HTTP rechaza entradas inválidas sin movimientos y persiste después exactamente
las cantidades 2 y 1 para plancha/retazo. Se inyecta únicamente la BD poseída;
no se simula la validación ni la persistencia.

## Validación final y alcance

| Comando | Resultado |
| --- | --- |
| `npm.cmd run test:unit` | 103 passed; 0 fail/skip |
| `npm.cmd run test:component` | 211 passed; 21 archivos |
| `npm.cmd run lint` | OK |
| `npm.cmd run build` | OK |
| `python -m pytest tests/unit/inventory tests/api/inventory tests/integration/inventory tests/integration/test_ta036_migration.py tests/unit/modules/orders tests/integration/modules/orders tests/api/orders -q --tb=short` | 644 passed |
| `python -m pytest -q --tb=short` | 1330 passed |
| `python -m alembic heads` | ta036a1b2c3d (head único) |

Python usa el intérprete local instalado y pruebas con dotenv deshabilitado,
PostgreSQL requerido y timeout de pg_ctl de 85 segundos. Único warning backend:
deprecación existente httpx/Starlette TestClient. No se modificó configuración
de pruebas para omitir checks o permitir SQLite. El suite completo incluye
los contratos geométricos backend y pedidos, incluido POST sin stock.
En `test_register_order_without_inventory_and_cancel_moves_it_to_end` se
comprueba en PostgreSQL que Plancha y Retazo están vacíos antes de crear dos
pedidos vía HTTP; ambos se registran y cancelar el segundo lo coloca al final.
La persistencia/servicio de pedidos no se reemplaza por un mock de stock.

Único archivo de producción cambiado por este correctivo:
`backend/app/modules/inventory/infrastructure/repository.py` (guarda de cantidad
antes del insert). Se modifican seis archivos de tests, esta evidencia y la
aclaración de SPEC. No se cambia UI, algoritmo geométrico, API de estado,
consulta de stock, migración ni infraestructura.

Recomendación: **GO para T06** por cobertura vigente restablecida y validaciones
aprobadas. T06 permanece sin ejecutar; la revisión humana/Draft conserva su
estado previo. No hay decisión de esquema pendiente bajo la SPEC actual.
