# Último correctivo funcional: ángulos y JSON de retazos

Fecha: 13/10/2026. Rama `feature/TA-036-saneamiento-funcional`, HEAD conservado
`fa13b0020fcee57a8368d54b0d4e980a41630d3e`. Cambios locales sin commit, incluidos
los de [editor y navegación](ajuste-editor-navegacion.md), preservados.

Lo anterior describe el estado al entregar el correctivo para retest. El
cierre posterior confirmado por el usuario se registra al final de este
documento; conserva la trazabilidad sin reescribir los resultados previos.

## Trazabilidad y causas

Revisión técnica previa → validación manual → ajuste del editor/navegación →
dos hallazgos manuales → este correctivo → retest automatizado → pendiente
retest manual del usuario. No es revisión humana ni aprobación formal.

1. **Ángulos:** el editor tenía configuración cíclica por defecto y un atajo
   de V2 exclusivo de cuadriláteros. `interiorAngles` solo mostraba valores
   derivados; no había colección de restricciones seleccionables para n lados.
   Los lados se almacenaban en `segments[].lengthMm`; el solver construía
   `vertices_mm`. Se extiende esa base, sin sustituir su constructor cíclico.
2. **Decimal:** el frontend manda números JSON. `PoligonoConvexo.vertices_mm`
   valida `list[tuple[Decimal, Decimal]]`. `model_dump()` Python conserva esas
   tuplas y Decimal; DTO y servicio hacen copias y validan área sin convertirlos.
   `_encode_geometria` del repositorio recorría dict/list, pero no tuple. La
   geometría asignada al atributo JSONB de `Retazo` todavía contenía
   `vertices_mm[i] = (Decimal(...), Decimal(...))` antes de `session.flush()`.
   Psycopg falla determinísticamente al serializarlo. Las formas estándar
   funcionan porque sus Decimal están en el diccionario y sí se recorrían.

La regresión HTTP/PostgreSQL se ejecutó **antes** del fix: primer triángulo
falló con `TypeError: Object of type Decimal is not JSON serializable`.
No se observó `OperationalError`; no se atribuye ese evento previo a este bug.

## Solución angular y contrato

- Todos los lados siguen editables individualmente. Se retira el reescalado
  automático de campos de la UI: cambiar S2 nunca modifica S1/S3/etc.
- Máximo n−3 restricciones en vértices diferentes: triángulo 0, cuadrilátero 1,
  pentágono 2, hexágono 3. UI y función pura hacen cumplir el límite.
- Cada fila identifica V y los lados adyacentes. «Fijar ángulo» crea un input
  marcado Fijado; «Liberar ángulo» lo devuelve a Calculado. Se muestran usados
  y permitidos; al alcanzar el límite se deshabilitan nuevas fijaciones.
- Etiquetas V1…Vn en ambos SVG y resaltado asociado al foco ayudan a identificar
  el vértice. Botones e inputs tienen nombres accesibles y funcionan con teclado.
- El boceto aporta orden, orientación y punto de partida. Nunca mide ángulos
  exactos. La topología dibujada debe ser simple convexa en el alcance actual.
- Sin ángulos fijados se puede elegir configuración cíclica o búsqueda desde
  el boceto. Con restricciones angulares, se resuelven esas restricciones sin
  imponer además conciclicidad. Para cambiar configuración se liberan primero.
- `angularConstraints.js` resuelve direcciones de aristas con longitudes
  normalizadas exactas, cierre y ángulos seleccionados mediante mínimos
  cuadrados amortiguados. Usa el boceto, la solución cíclica y puntos de partida
  alternativos deterministas. No altera los valores introducidos.
- La iteración no es certificado de validez: después se comprueban todos los
  lados, ángulos fijados, suma, cierre implícito, área, convexidad y simplicidad.
  Se rechaza el resultado que no satisfaga esas comprobaciones.
- Tolerancias: error relativo por lado **1e−7**; por ángulo fijado **1e−5 grados**;
  suma angular **n×1e−5 grados** respecto a `(n−2)×180`; residual de cierre
  normalizado **≤1e−9**. Política convexa compartida: tolerancia relativa **1e−9**.
- No se garantiza búsqueda exhaustiva de todas las configuraciones posibles.
  El mensaje dice «No se encontró…», permite revisar/liberar restricciones o
  cambiar boceto y bloquea confirmar. No confunde falta de convergencia con una
  prueba matemática de inexistencia. Se rechazan rangos numéricos degenerados.
- `vertices_mm` sigue siendo el resultado canónico final. Las restricciones
  viven en el borrador de edición, no reemplazan los vértices persistidos.
  La convexidad es política separada; no se habilitan cóncavos ni se toca raster.
- Retazos usan exactamente el mismo `CustomPieceEditor`; no hay editor angular
  paralelo. Geometrías existentes sirven de punto de partida al reabrirlas.

## Fronteras JSON

El normalizador existente ahora recorre también tuplas, convirtiéndolas en
listas y sus Decimal en int/float. Corre en Infrastructure antes de asignar
JSONB, para POST y PATCH. No se usa FastAPI en Infrastructure ni `default=str`.
Decimal se conserva para validar y calcular en dominio/aplicación.

Además, el serializer HTTP de `vertices_mm`, activo solo en modo JSON,
devuelve números. El dump Python que alimenta DTOs sigue siendo Decimal.
Sin cambios semánticos del formato, ORM, esquema ni migraciones.

Cinco casos parametrizados atraviesan HTTP → schemas → servicio → repositorio
→ PostgreSQL real temporal: triángulo, cuadrilátero, coordenadas fraccionarias,
rectángulo y círculo. Verifican 201, listado recuperable, PATCH 200 y JSONB
numérico mediante `jsonb_typeof`. Solo se inyecta la base aislada; servicio,
repositorio, autenticación y driver son reales.

## Validación ejecutada

Entorno: Python 3.11 de `backend/venv`, `PYTHON_DOTENV_DISABLED=1`,
`NEWGLASS_REQUIRE_POSTGRES=1`, `PGCTLTIMEOUT=85`. E2E antepone ese venv al PATH;
API y PostgreSQL creados por el launcher son locales aislados. En PowerShell
se usa `npm.cmd` para los scripts npm indicados.

| Comando | Resultado |
| --- | --- |
| `python -m pytest tests/integration/inventory tests/api/inventory tests/unit/inventory tests/unit/modules/orders/domain/test_domain_geometry.py -q` | 518 passed; 51,00 s. |
| `python -m pytest -q` | 1335 passed; 346,11 s; cero fallos. |
| `npm run test:unit` | 124 passed; cero fallos/skips. |
| `npm run test:component` | 223 passed; 23 archivos; 22,27 s; cero fallos. |
| `npm run lint` | Exit 0. |
| `npm run build` | Exit 0; build local normal. |
| `npm run test:e2e -- tests/e2e/hu007-custom-piece.spec.js tests/e2e/ta036-retazo-personalizado.spec.js` | 32 descubiertos/passed; cero fallos/skips; 42,1 s. |
| `npm run test:e2e` | 46 descubiertos, 45 passed, 0 failed, 1 skipped; 49,9 s. |

Ambas ejecuciones E2E usan Chrome local en proyectos chromium-desktop y
chromium-mobile. Único skip de la suite completa: HU-014 móvil,
«Almacenero registra una baja y consulta el movimiento persistido». Motivo
preexistente sin cambios: «La mutación agota un recurso compartido entre
viewports.» El caso se ejecuta en desktop; el skip no se cuenta como éxito.
El nuevo registro de retazo personalizado pasa en ambos viewports.

Backend informa un warning existente de deprecación TestClient/httpx. No es
fallo ni skip. La primera ejecución focalizada E2E detectó dos aserciones del
mismo caso que aún buscaban el ángulo como texto calculado; se actualizaron al
input Fijado y toda la focalizada pasó. Durante adaptación de componentes se
corrigieron expectativas obsoletas de reescalado y un matcher numérico; un
timeout de 5 s bajo ejecución concurrente con backend no volvió en la suite
final. No se incrementaron timeouts ni se silenciaron pruebas.

Delta respecto al estado recibido: +9 unitarias, +4 componentes, +5 backend,
+6 ejecuciones E2E (pentágono, hexágono y retazo × desktop/mobile). No se eliminan
tests ni se cambia descubrimiento/configuración. Los tests previos de escala
introducen ahora todas las medidas explícitamente; los dos que exigían
reescalado automático validan conservación de campos y transformación final.

## Archivos y límites

Backend de este correctivo:

- `backend/app/modules/inventory/infrastructure/repository.py`
- `backend/app/modules/inventory/presentation/schemas.py`
- `backend/tests/integration/inventory/test_repository.py`

Frontend de este correctivo, además de preservar los cambios previos:

- `frontend/src/features/orders/CustomPieceEditor.jsx` y `.css`
- `frontend/src/features/orders/constrainedGeometry.js`
- `frontend/src/features/orders/angularConstraints.js` (nuevo)
- `frontend/src/features/orders/__tests__/CustomPieceEditor.test.jsx`
- `frontend/src/features/orders/__tests__/ConstrainedPieceEditor.test.jsx`
- `frontend/src/features/orders/__tests__/NuevoPedido.test.jsx`
- `frontend/src/features/inventory/__tests__/RegistrarRetazoGeometry.test.jsx`
- `frontend/tests/unit/constrainedGeometry.test.js`
- `frontend/tests/e2e/hu007-custom-piece.spec.js`
- `frontend/tests/e2e/ta036-retazo-personalizado.spec.js` (nuevo)

Navegación no se rediseña. Regresión de App/Sidebar y permisos pasa; el usuario
confirmó mantener Pedidos, Inventario y Roles. Inicio, Resultados y
Configuración no tienen pantallas funcionales en esta rama; no se presentan
como funcionalidad implementada. Header conserva identidad/rol/cerrar sesión.

SPEC permanece **Draft**, reviewer pendiente; **CA-09 PARTIAL** con su criterio
sin cambios. No se absorbe HU-008 ni se modifica rasterización de Aguilar.
No commit, push, PR, merge, reset, restore, rebase, stash ni nuevos worktrees.
No Staging, Supabase, Heroku, Pages ni despliegue. La revisión técnica anterior
no certifica automáticamente este correctivo posterior.

## Retest manual preparado

Usar la aplicación local con datos de prueba. En Pedidos seleccionar cliente,
material/espesor válidos y agregar pieza Personalizada. Dibujar vértices en
orden alrededor de un contorno convexo, cerrar e introducir cada longitud.

1. **Triángulo:** 50/70/65. Debe aceptar; mostrar tres ángulos Calculado y
   «0 de 0 utilizadas», sin botones Fijar ni inputs angulares. Suma ≈180°.
2. **Triángulo inválido:** cambiar a 10/10/30. Debe explicar la desigualdad de
   cierre, retirar geometría válida anterior e impedir agregar/guardar.
3. **Cuadrilátero:** 120/73/91/108. Pulsar Fijar ángulo V2, escribir 75 y luego
   100. Los cuatro campos de longitud permanecen, cambia la vista final y V2
   aparece Fijado. Contador 1 de 1; otra fijación deshabilitada. Suma ≈360°.
4. **Pentágono:** 80/115/63/92/71. Fijar V2=90 y V3=102, combinación compatible.
   Debe aceptar, mostrar 2 de 2 e impedir una tercera fijación; suma ≈540°.
   Liberar V2, luego fijar V1 conservando el valor propuesto, y comprobar que
   vuelve a permitir dos restricciones sin modificar longitudes.
5. **Hexágono irregular:** 80/115/63/92/71/98. Fijar V2=106, V3=117.5, V4=127.
   Debe aceptar, distinguir tres Fijado/tres Calculado y mostrar 3 de 3.
   Impedir cuarta fijación. Cambiar V2 ligeramente y comprobar nueva forma
   conservando lados; suma ≈720°. Un ángulo 0/180 debe invalidar sin borrar inputs.
6. **Retazo:** Inventario → pestaña Retazos → Registrar retazo → código único,
   tipo/espesor válidos → Personalizado. Dibujar cuadrilátero, introducir
   120/73/91/108, fijar V2=100 y pulsar Registrar retazo. Debe responder 201,
   aparecer en inventario y conservar números en `geometria.vertices_mm` del
   POST/listado. No hay botón adicional de confirmar pieza: este formulario
   recibe la geometría válida del editor y confirma al registrar el retazo.
7. **Regresión de navegación:** cambiar entre módulos permitidos desde sidebar;
   header sin enlaces duplicados. Probar cierre de sesión.

Pendiente exclusivamente retest manual y posterior decisión humana; no se
marca Reviewed/Implemented/Verified ni se realiza commit por cuenta propia.

Resultado técnico: **READY FOR FINAL MANUAL RETEST**. `git diff --check` sin
errores. Cambios locales sin staging ni commit; HEAD y rama conservados.

## Cierre tras retest manual satisfactorio — 13/10/2026

El usuario confirmó textualmente: «El retest manual final de TA-036 fue
satisfactorio». Sobre esa confirmación autorizó organizar y commitear los
cambios locales actuales en cuatro bloques, sin push ni merge. No se
atribuye al agente una ejecución manual adicional ni se inventa una lista
de resultados manuales individuales que el usuario no haya proporcionado.

Se preservan los resultados automatizados anteriores: backend 1335 passed,
frontend 124 unitarias y 223 componentes, lint/build OK, E2E focalizado 32
passed y completo 45 passed/0 failed/1 skip móvil HU-014 conocido. Durante la
organización en commits no se cambia producción ni se vuelven a ejecutar
esas suites; se revisa el diff staged y los checks de whitespace por bloque.

Commits funcionales: geometría exacta y editor compartido `6062f22`, navegación
sidebar/header `5b881eb`, persistencia JSON y su E2E `80b8aef`.
El cuarto registra esta evidencia y la confirmación manual.
Los cuatro mensajes son los solicitados por el usuario.

No se incluyen logs, temporales, archivos de entorno ni credenciales reales.
Las cuentas E2E son fixtures sintéticos locales. Sin push, PR, merge ni deploy.
La SPEC sigue **Draft**, reviewer pendiente; **CA-09 PARTIAL**, sin alterar
el criterio. Retest funcional satisfactorio no equivale a revisión formal
independiente ni permite marcar Reviewed/Implemented/Verified automáticamente.
