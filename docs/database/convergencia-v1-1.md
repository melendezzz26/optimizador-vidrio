# Convergencia del modelo de datos a v1.1

## Línea base normativa

El documento aprobado `Documento_Diseno_Base_Datos_NewGlass_v1_1.docx` define
el modelo objetivo: 12 entidades y 90 columnas. OPTIMIZACION tiene 9 columnas,
incluida `criterio_seleccion_version VARCHAR(20) NOT NULL`; `LEX-V1` es la
versión inicial del criterio de selección, sin añadir un default de BD.

## Estado remoto observado previamente

La inspección anterior, realizada en modo solo lectura, observó una única fila
en `public.alembic_version`: `c4e8a1f2b3d5`. Las columnas y PK/FK/UNIQUE
comparadas coincidían con el resultado esperado de las migraciones de HU-003.
Este registro describe aquella inspección; no se volvió a consultar Supabase
durante la recuperación del historial.

## Recuperación de la historia en Git

El main de partida contenía únicamente `9b9f04eb67f6`. Se recuperó desde
`origin/feature/HU-003-gestion-usuarios` el archivo
[`c4e8a1f2b3d5_hu003_agregar_dni_y_usuario.py`](../../backend/alembic/versions/c4e8a1f2b3d5_hu003_agregar_dni_y_usuario.py),
sin cambios de contenido y conservando:

```text
revision = c4e8a1f2b3d5
down_revision = 9b9f04eb67f6
```

La recuperación restaura la correspondencia entre la historia disponible en
Git y el esquema remoto observado. No crea una migración equivalente ni duplica
la incorporación de DNI/usuario. No se hizo cherry-pick del commit completo
`809a2b7` ni se incorporaron su CRUD, frontend o imports funcionales.

La migración no se vuelve a ejecutar sobre Supabase: su revisión ya estaba
registrada y sus cambios estructurales estaban presentes en la inspección.

## Validación local de la restauración (anterior a R1)

Desde `backend/`, usando el Python del entorno virtual en PowerShell:

```powershell
& ./venv/Scripts/python.exe -B -m alembic history
& ./venv/Scripts/python.exe -B -m alembic heads
```

Salida de `alembic history` (código 0):

```text
9b9f04eb67f6 -> c4e8a1f2b3d5 (head), HU-003: agregar dni y usuario a usuarios; correo pasa a opcional
<base> -> 9b9f04eb67f6, crear esquema inicial
```

Salida de `alembic heads` (código 0):

```text
c4e8a1f2b3d5 (head)
```

En esa fase existía un único head local. Estos comandos, con la configuración y opciones
utilizadas, leen los scripts locales sin ejecutar `env.py` ni conectarse a la BD.
No se ejecutaron `current`, `upgrade`, `downgrade`, `stamp` ni `revision`.

## R1: identidad, inventario y pedidos

La revisión preparada manualmente es
[`e1a2b3c4d5f6`](../../backend/alembic/versions/e1a2b3c4d5f6_r1_identidad_inventario_pedidos.py),
con `down_revision = c4e8a1f2b3d5`. Conserva ambos archivos históricos sin
alterarlos y no repite la creación de DNI/usuario. Las siguientes revisiones
continuarán esta cadena.

R1 alinea únicamente los siete modelos en
[`models.py`](../../backend/app/models.py) y su migración correspondiente:

| Entidad | Cambio R1 |
| --- | --- |
| ROL | `nombre VARCHAR(30)`, `descripcion VARCHAR(150) NULL`; conserva PK y UNIQUE de nombre. |
| USUARIO | Incorpora DNI/usuario al ORM; DNI `CHAR(8)`, patrones, fecha de creación `TIMESTAMPTZ NOT NULL`, estado con default de servidor `TRUE`; retira correo y su UNIQUE. |
| TIPO_VIDRIO | UNIQUE de nombre y default de servidor `TRUE` para estado. |
| PLANCHA | Stock agregado sin código; dimensiones `NUMERIC(10,2)`, espesor `NUMERIC(4,1)`, CHECK de dimensiones positivas, espesor admitido y cantidad no negativa; fecha de registro con zona e índice de stock compatible. |
| RETAZO | Código `VARCHAR(40)`, espesor `NUMERIC(4,1)`, área `NUMERIC(18,2)` positiva, fecha de registro con zona e índice de stock compatible. |
| PEDIDO | Fecha con zona, estado `VARCHAR(20)` y dominio exacto; espesor `NUMERIC(4,1)`; renombra `id_usuario` a `id_usuario_registro` conservando la FK; índice de estado/fecha. |
| PIEZA | Forma `VARCHAR(30)` con dominio exacto, cantidad positiva, geometría obligatoria y área `NUMERIC(18,2) NOT NULL` positiva; dimensiones JSONB opcionales. |

Los espesores admitidos son `3, 4, 5.5, 6, 8` mm. Los estados de pedido son
`PENDIENTE`, `EN_OPTIMIZACION`, `OPTIMIZADO`, `CONFIRMADO`, `CANCELADO`; las formas
son `RECTANGULO`, `CIRCUNFERENCIA`, `POLIGONO_CONVEXO`.
Los cuatro estados booleanos de usuario/tipo/plancha/retazo tienen default de
servidor `TRUE`. Ninguna fecha tiene default de servidor ni se deduce su zona
histórica. El ORM requiere fechas explícitas con zona; se retira el anterior
`datetime.now` sin zona de Pedido. Se conserva su default Python preexistente
`PENDIENTE`, sin convertirlo en default de servidor.

Las PK y FK existentes se conservan; no se añaden cascadas. Los UNIQUE de DNI
y usuario se reutilizan, sin índices duplicados. No se deduplican planchas ni
se impone una nueva clave compuesta para stock.

### Políticas aprobadas y precondiciones

1. **Correo:** respaldo seguro fuera del repositorio antes de aplicar R1 a la
   base compartida. La migración elimina columna y UNIQUE; no crea archivos,
   columnas alternativas ni historial de datos personales. El respaldo es una
   precondición operativa, no una acción automática de la migración.
2. **Fecha del usuario heredado:** el timestamp de ejecución de la sentencia
   de incorporación es una fecha técnica de ingreso al esquema v1.1. No
   representa necesariamente su alta histórica. Se rellena una sola vez y
   luego se exige NOT NULL, sin default permanente. Las altas posteriores
   deben proporcionar su fecha real.
3. **Plancha/retazo:** deben seguir vacíos. Si hay filas, se aborta; no se
   inventan fechas históricas. Si están vacíos, se añade directamente la
   fecha de registro obligatoria.
4. **Pedido:** debe seguir vacío. Si tiene filas, se aborta antes del DDL;
   no se interpreta como UTC ni como America/Lima ningún timestamp heredado.
5. **Pieza:** se aborta ante geometría o área SQL NULL; no se generan geometrías,
   no se rellena con cero ni se borran filas. La presencia de pedidos también
   impide ejecutar R1 según la política anterior.
6. **Conversiones:** se comprueban longitudes, finitud, dominios, rango, escala
   y conservación del valor al convertir FLOAT a NUMERIC y volver a FLOAT.
   Se aborta ante truncamiento, redondeo o pérdida de precisión; no hay
   normalizaciones automáticas. Se comprueban duplicados de tipos de vidrio.
7. **Identificador de acceso:** CHECK de una letra ASCII, sin imponer su caso,
   seguida de ocho dígitos; DNI con ocho dígitos. No se compara el identificador
   permanentemente con nombres ni se cambia al renombrar al trabajador.
   La normalización inicial pertenece a la aplicación.

Las siete tablas se bloquean durante la transacción antes del preflight para
evitar escrituras entre comprobaciones y transformaciones. Todas las
precondiciones se verifican antes del primer cambio de esquema/datos. Un fallo
posterior también debe revertir la transacción completa y conservar la revisión.
Estos bloqueos requieren una ventana coordinada antes de cualquier aplicación
compartida. No se usa CASCADE para eliminar dependencias imprevistas.

### Alcance diferido y compatibilidad

R1 mantiene **10 tablas y 68 columnas** en la metadata, todavía no las 12
entidades/90 columnas del objetivo completo. Los siete modelos R1 suman 45
columnas. `Retazo.id_ejecucion_origen` y su FK nullable se incorporarán en una
revisión posterior al alinear EJECUCION_OPTIMIZACION; no se enlazan ahora a la
estructura histórica de ejecuciones ni se sustituye esa relación por otro campo.

CONFIGURACION, EJECUCION_OPTIMIZACION y METRICA_EJECUCION conservan sus estructuras
actuales. OPTIMIZACION y MATERIAL_UTILIZADO no se crean. No se implementan
heurísticas, confirmación de inventario ni validadores geométricos: el contrato
JSONB deberá validarse en la SPEC/aplicación correspondiente.

El ORM R1 deja de ser compatible con el esquema remoto todavía observado en
HU-003. No debe desplegarse contra él sin coordinar la migración. Los futuros
consumidores deben usar `usuario`, `id_usuario_registro`, fechas explícitas con
zona y valores Decimal. El CRUD de HU-003 que usa correo debe adaptarse antes
de integrarse; no se ha importado en este cambio.

La revisión no ofrece downgrade automático: los correos/códigos retirados no
pueden reconstruirse. Su función `downgrade()` aborta expresamente; cualquier
recuperación requiere un procedimiento revisado y respaldo externo.

### Validación de R1 anterior a R2

Las pruebas de metadata no abren conexiones. Las de integración crean su propio
clúster PostgreSQL temporal, escuchando únicamente en `127.0.0.1` y con puerto
efímero; utilizan datos sintéticos. No leen la URL remota para elegir destino y
no utilizan el servicio PostgreSQL existente. No se usa SQLite como sustituto
de estas pruebas de migración.

Los binarios se buscan en PATH, en `NEWGLASS_TEST_PG_BIN` o en la instalación
Windows de PostgreSQL 18. Sin binarios las pruebas de integración se marcan
como omitidas; ese resultado no demuestra que la migración funcione.

Desde `backend/`:

```powershell
& ./venv/Scripts/python.exe -B -m pytest -q
& ./venv/Scripts/python.exe -B -m alembic history
& ./venv/Scripts/python.exe -B -m alembic heads
```

Desde la raíz: `git diff --check`.

La suite aplica `upgrade` exclusivamente a sus bases temporales. Comprueba el
recorrido desde una BD limpia, transformación de una cuenta sintética heredada,
metadata frente al esquema migrado, constraints y conservación del estado ante
errores. No ejecuta downgrade, stamp, seed ni operaciones contra Supabase.

Resultado local obtenido con PostgreSQL **18.6** aislado:

- `pytest -q`: **78 passed in 39.86s**, sin omisiones (20 pruebas previas,
  8 pruebas nuevas de metadata y 50 de integración).
- [`test_r1_models.py`](../../backend/tests/unit/test_r1_models.py): tipos,
  nulabilidad, PK/FK/UNIQUE/CHECK, defaults, índices, campos retirados/diferidos
  y conservación de las entidades excluidas.
- [`test_r1_migration.py`](../../backend/tests/integration/test_r1_migration.py):
  migración desde vacío y desde HU-003 con cuenta sintética; comparación
  esquema/ORM sin diferencias; preflight de datos inválidos; constraints;
  rollback de DDL y fecha técnica ante una vista dependiente de correo.
- `git diff --check`: sin incidencias.

`alembic history` (lectura local, código 0):

```text
c4e8a1f2b3d5 -> e1a2b3c4d5f6 (head), R1: alinear identidad, inventario y pedidos con el modelo v1.1.
9b9f04eb67f6 -> c4e8a1f2b3d5, HU-003: agregar dni y usuario a usuarios; correo pasa a opcional
<base> -> 9b9f04eb67f6, crear esquema inicial
```

`alembic heads` (lectura local, código 0):

```text
e1a2b3c4d5f6 (head)
```

La prueba en PostgreSQL 18.6 no sustituye la revisión de compatibilidad con la
versión/configuración del entorno de destino ni autoriza aplicar R1 allí.
Antes de hacerlo siguen siendo necesarios el respaldo externo, la coordinación
de consumidores y la verificación de las precondiciones/demás dependencias del
esquema compartido. No se ha ejecutado ninguna migración sobre Supabase.

Se conserva una limitación histórica de `c4e8a1f2b3d5`: su `upgrade()` aborta
si `usuarios` contiene cualquier registro. Completar DNI no evita esa condición.
Esto debe contemplarse al probar otros entornos que todavía estén en la revisión
inicial; no justifica borrar usuarios, repetir la migración remota ni alterar
la revisión registrada para eludirla.

No hubo conexiones ni modificaciones de datos remotos durante la preparación
de R1. La revisión remota reportada anteriormente sigue siendo un antecedente,
no una nueva observación ni una afirmación de que R1 esté aplicada allí.

## R2: CONFIGURACION como snapshot versionado

La revisión
[`f2b3c4d5e6a7`](../../backend/alembic/versions/f2b3c4d5e6a7_r2_configuracion_versionada.py)
desciende de `e1a2b3c4d5f6`. Las tres revisiones anteriores no se modifican.
R2 cambia exclusivamente la estructura de CONFIGURACION; mantiene su PK,
secuencia de identificación y la FK entrante desde
`ejecuciones_optimizacion.id_configuracion`.

### Precondición obligatoria: tabla vacía

Antes de cualquier DDL, la revisión bloquea `configuraciones` mediante
`LOCK TABLE ... IN ACCESS EXCLUSIVE MODE` y ejecuta
`SELECT COUNT(*) FROM configuraciones`. Si existe cualquier fila, lanza un
`RuntimeError` descriptivo y no modifica columnas ni datos. El bloqueo se
mantiene hasta terminar la transacción Alembic para evitar inserciones entre
la comprobación y los cambios. La migración es atómica.

No se interpretan unidades históricas, no se transforma área en dimensiones,
no se copia una dimensión a ambos mínimos ni se reutiliza una fecha histórica.
No se inventan versiones, creador, vigencia o fechas. Los renombres y cambios
de tipos solo se realizan sobre una tabla vacía. No se insertan configuraciones.

### Estructura final de CONFIGURACION

| Columna | Tipo | Restricciones |
| --- | --- | --- |
| id_configuracion | INTEGER | PK, NOT NULL; conserva generación existente |
| version | INTEGER | UNIQUE, NOT NULL, CHECK > 0 |
| separacion_mm | NUMERIC(8,2) | NOT NULL, CHECK >= 0 |
| margen_mm | NUMERIC(8,2) | NOT NULL, CHECK >= 0 |
| resolucion_raster_mm | NUMERIC(8,3) | NOT NULL, CHECK > 0 |
| paso_angular_grados | NUMERIC(6,2) | NULL, CHECK > 0 AND <= 360 |
| ancho_min_retazo_mm | NUMERIC(10,2) | NOT NULL, CHECK >= 0 |
| alto_min_retazo_mm | NUMERIC(10,2) | NOT NULL, CHECK >= 0 |
| vigente | BOOLEAN | NOT NULL, DEFAULT TRUE |
| id_usuario_creacion | INTEGER | NOT NULL, FK usuarios.id_usuario |
| fecha_creacion | TIMESTAMPTZ | NOT NULL |

Se ratificó expresamente que `paso_angular_grados` admite NULL: v1.1 no prescribe
NOT NULL para ese campo. Su CHECK combinado constituye una de las siete
restricciones CHECK de CONFIGURACION.

Los renombres son `resolucion_raster` a `resolucion_raster_mm`, `paso_angular` a
`paso_angular_grados` y `fecha_actualizacion` a `fecha_creacion`. Se eliminan
`area_minima_retazo` y `dimension_minima_retazo`. Los cinco nombres anteriores
ya no forman parte del ORM vigente.

`vigente` es el único nuevo default de servidor. No hay defaults Python en
CONFIGURACION: se retira `datetime.now` del campo temporal anterior y las
creaciones futuras deberán proporcionar fecha, responsable, versión y
parámetros. No se agregan índices adicionales a los que respaldan PK/UNIQUE,
ni cascadas para las FK.

Después de R2, la metadata contiene **10 tablas y 71 columnas**; CONFIGURACION
tiene **11 columnas**. El total 68 registrado anteriormente corresponde a R1.

### Semántica y alcance diferido

La estructura permite snapshots versionados. Cambiar parámetros debe crear
una nueva versión; una configuración utilizada no debe modificarse. La
asignación secuencial, la coordinación concurrente y la inmutabilidad serán
responsabilidad de la futura capa de aplicación/persistencia. El esquema R2
por sí solo no garantiza esas reglas.

No se implementan triggers de inmutabilidad, secuencias adicionales,
`MAX(version)+1`, lógica de versionado ni UNIQUE parcial de `vigente`.
Varias configuraciones pueden tener `vigente = TRUE`.

Los siete modelos alineados por R1, EJECUCION_OPTIMIZACION y METRICA_EJECUCION
permanecen estructuralmente intactos. OPTIMIZACION y MATERIAL_UTILIZADO no se
crean; `Retazo.id_ejecucion_origen` continúa diferido. No se modifican endpoints
ni se implementan heurísticas.

El `downgrade()` de R2 falla explícitamente con `RuntimeError`: no puede
reconstruir de forma segura los campos retirados ni su semántica. No ofrece una
reversión aparente mediante un `pass` ni rellena campos históricos. Cualquier
recuperación exige un procedimiento revisado.

### Pruebas y validación de R2

- [`test_r2_models.py`](../../backend/tests/unit/test_r2_models.py) valida las
  once columnas, tipos, nulabilidad, defaults, PK/FK/UNIQUE, siete CHECK,
  ausencia de índices adicionales, conteo 10/71 y cadena lineal. También
  comprueba, mediante una llamada Python sin conexión, que `downgrade()` falla.
- [`test_r2_migration.py`](../../backend/tests/integration/test_r2_migration.py)
  prueba el recorrido desde vacío hasta head, R1 a R2, rechazo de una fila
  heredada, rollback ante una vista dependiente, invariancia de las otras nueve
  tablas/secuencias y comparación del esquema final con el ORM vigente.
  Verifica restricciones, límites NUMERIC, paso angular NULL y varias filas
  vigentes en PostgreSQL real.
- Las pruebas específicas de R1 apuntan ahora a `e1a2b3c4d5f6`, no a `head`.
  Su contrato histórico de CONFIGURACION se verifica explícitamente con ocho
  columnas, los nombres anteriores y el total de 68 columnas. Las siete
  entidades R1 conservan sus pruebas. La comparación completa del ORM vigente
  con head se realiza en R2.
- Las utilidades PostgreSQL se comparten mediante
  [`postgres_support.py`](../../backend/tests/integration/postgres_support.py)
  y su fixture en `conftest.py`: clúster temporal, puerto propio en loopback,
  datos sintéticos y parada al terminar. No se usa el servicio existente ni
  la URL remota como destino. Sin binarios locales, la integración se omite
  explícitamente; una omisión no constituye evidencia de migración aprobada.

Los comandos de validación siguen siendo `python -m pytest -q`,
`alembic history`, `alembic heads` y `git diff --check`. Los upgrades de las
pruebas se ejecutan únicamente en el clúster aislado. No se ejecuta el comando
Alembic downgrade, stamp ni seed. R2 no se aplica a Supabase.

Resultado local de esta fase, en PostgreSQL **18.6** temporal y aislado:

```text
113 passed in 101.91s (0:01:41)
```

Sin omisiones ni errores: las 78 pruebas anteriores adaptadas y 35 nuevas
(4 unitarias y 31 de integración R2). La comparación del esquema migrado con
el ORM no produjo diferencias. El clúster de pruebas se detuvo al finalizar.
La comparación de las clases ORM con el commit R1 confirma que solo cambió
CONFIGURACION. `git diff --check` finaliza sin incidencias.

`alembic history` (lectura local, código 0):

```text
e1a2b3c4d5f6 -> f2b3c4d5e6a7 (head), R2: alinear CONFIGURACION con snapshots del modelo v1.1.
c4e8a1f2b3d5 -> e1a2b3c4d5f6, R1: alinear identidad, inventario y pedidos con el modelo v1.1.
9b9f04eb67f6 -> c4e8a1f2b3d5, HU-003: agregar dni y usuario a usuarios; correo pasa a opcional
<base> -> 9b9f04eb67f6, crear esquema inicial
```

`alembic heads` (lectura local, código 0):

```text
f2b3c4d5e6a7 (head)
```

No se ha consultado ni modificado Supabase durante R2. Esta evidencia local no
afirma que las revisiones R1/R2 estén aplicadas en el entorno remoto, ni acredita
que CONFIGURACION siga vacía allí. Su futura aplicación requerirá coordinación
con los consumidores y cumplimiento efectivo de la precondición aprobada.

## R3: trazabilidad de optimización y material propuesto

La revisión
[`a3c4d5e6f7b8`](../../backend/alembic/versions/a3c4d5e6f7b8_r3_trazabilidad_optimizacion.py)
tiene `down_revision = f2b3c4d5e6a7`. No se modifican revisiones anteriores.
Introduce OPTIMIZACION y MATERIAL_UTILIZADO, alinea EJECUCION_OPTIMIZACION y
añade exclusivamente `Retazo.id_ejecucion_origen` al contrato de inventario.

### Datos heredados y atomicidad

Antes del primer DDL se bloquean conjuntamente `ejecuciones_optimizacion` y
`metricas_ejecucion` con `ACCESS EXCLUSIVE` y se consulta `COUNT(*)` de ambas.
Si cualquiera contiene filas, se lanza `RuntimeError` sin ejecutar DDL ni
modificar datos o `alembic_version`. El bloqueo se conserva hasta finalizar
la transacción, evitando escrituras entre la comprobación y los cambios.

No se inventan corridas, responsables, estados, completitud o fechas; no se
agrupa por pedido/configuración ni se interpreta `seleccionada`. No se asume
que una ejecución heredada usó LEX-V1 ni se traslada `tiempo_computacional`
a métricas sin conocer su unidad. La ausencia de filas es una precondición
comprobada en cada ejecución, no una suposición basada en inspecciones previas.

RETAZO puede contener datos: sus filas se conservan y la nueva columna nullable
queda NULL, sin atribuirles un origen histórico. La transacción también revierte
los cambios si una dependencia inesperada impide un DDL posterior. No se usa
CASCADE para eliminar dependencias.

### Contrato estructural

| Tabla | Columnas y reglas R3 |
| --- | --- |
| optimizaciones | 9: PK `id_optimizacion`; fechas inicio/fin TIMESTAMPTZ, fin nullable; estado VARCHAR(20); FK obligatorias a pedido, configuración y usuario ejecutor; `criterio_seleccion_version VARCHAR(20) NOT NULL`; selección nullable con FK a ejecución. |
| ejecuciones_optimizacion | 8: PK `id_ejecucion` conservada; FK obligatoria `id_optimizacion`; método VARCHAR(10); inicio TIMESTAMPTZ obligatorio y fin nullable; estado VARCHAR(20); completo BOOLEAN obligatorio sin default; patrón JSONB nullable. |
| materiales_utilizados | 5: PK `id_material_utilizado`; ejecución obligatoria; plancha/retazo nullable con XOR; cantidad INTEGER NOT NULL DEFAULT 1, CHECK > 0. |
| retazos | 9: las ocho columnas anteriores intactas más `id_ejecucion_origen INTEGER NULL`, FK a ejecución. |
| metricas_ejecucion | Sus siete columnas, tipos, nulabilidad, PK, UNIQUE y FK permanecen exactamente como en R2. |

OPTIMIZACION admite `EN_EJECUCION`, `COMPLETADA`, `SIN_SOLUCION` y `FALLIDA`.
EJECUCION admite `EN_EJECUCION`, `COMPLETADA` y `FALLIDA`; sus métodos son
`FF`, `BF`, `WF`, con `UNIQUE(id_optimizacion, metodo)`. No se añaden defaults
para fechas, estado, completitud, criterio, usuario o selección.

De EJECUCION se retiran `id_pedido`, `id_configuracion`, `tiempo_computacional`
y `seleccionada`, incluidas sus dos FK salientes antiguas. `fecha_ejecucion`
se renombra a `fecha_inicio` y cambia a TIMESTAMPTZ sobre tabla vacía. No se
interpreta ninguna zona histórica. `metodo` pasa de VARCHAR(30) a VARCHAR(10).
Se conservan `id_ejecucion` y `patron_resultado`, y se retiran los defaults
Python antiguos de fecha/selección.

El XOR de MATERIAL_UTILIZADO es:

```sql
CHECK ((id_plancha IS NOT NULL) <> (id_retazo IS NOT NULL))
```

Rechaza ambas fuentes o ninguna. `regla_fuente` no es una columna. Los únicos
índices explícitos nuevos son OPTIMIZACION `(id_pedido, fecha_inicio)` y
MATERIAL_UTILIZADO `(id_ejecucion)`; no se duplica el índice del UNIQUE compuesto.

La metadata vigente contiene **12 tablas y 86 columnas**, excluyendo la tabla
de control de Alembic. METRICA se alineará en R4, pasando de siete a once
columnas para completar las 90 columnas de v1.1.

### Resolución del ciclo y preservación de METRICA

1. Crear OPTIMIZACION con la columna de selección nullable, sin su FK todavía.
2. Adaptar EJECUCION mediante ALTER, conservando la tabla física y su PK.
3. Crear la FK de `EJECUCION.id_optimizacion` hacia OPTIMIZACION.
4. Crear CHECK y UNIQUE de EJECUCION.
5. Crear mediante `op.create_foreign_key` la FK de selección hacia EJECUCION.

Ambas FK terminan activas en la misma transacción. En SQLAlchemy la FK de
selección tiene nombre explícito y `use_alter=True`; la FK inversa también
tiene nombre. No se usan FK diferibles, cascadas ni FK compuestas adicionales.
No se hace DROP/CREATE de EJECUCION ni de METRICA: su referencia entrante a
`id_ejecucion` sigue siendo la misma FK y continúa operativa.

### Semántica que R3 no implementa

LEX-V1 es la versión inicial de selección y debe suministrarla la aplicación;
no es un default SQL. La FK de selección garantiza existencia, no pertenencia
a la misma corrida ni `completo = TRUE`: esas validaciones siguen en la capa
de aplicación según v1.1. El dominio de métodos y UNIQUE permiten como máximo
una ejecución FF, BF y WF por corrida; coordinar las tres pertenece al flujo
posterior, no a un trigger.

MATERIAL_UTILIZADO representa propuestas de cada ejecución. Insertarlo no
descuenta planchas, no cambia el estado de retazos y no crea sobrantes. No se
añaden triggers ni lógica de consumo, confirmación, selección o heurísticas.
La confirmación transaccional del inventario sigue pendiente.

El `downgrade()` falla explícitamente con `RuntimeError`: no es posible
reconstruir de forma segura el significado de los campos retirados. Cualquier
recuperación requiere un procedimiento revisado; no existe un `pass` silencioso.

### Pruebas históricas y validación de R3

Las pruebas R1/R2 migran a sus revisiones explícitas y conservan sus contratos
10/68 y 10/71. Para evitar compararlos contra el ORM que sigue evolucionando,
[`model_contracts.py`](../../backend/tests/model_contracts.py) carga un
[snapshot R1](../../backend/tests/contracts/r1_models.py) obtenido del commit
`9c8c3fb`; el contrato R2 incorpora únicamente la configuración aprobada en
`e1edde3`. Son fixtures de pruebas, no código importado por la aplicación, y
no requieren consultar Git durante pytest. Las pruebas anteriores se conservan.

- [`test_r3_models.py`](../../backend/tests/unit/test_r3_models.py): columnas,
  tipos, nulabilidad, defaults, PK/FK/UNIQUE/CHECK, índices, ciclo, cadena lineal,
  12/86 y preservación de las entidades fuera de alcance. La prueba de downgrade
  es una llamada Python sin conexión que verifica el RuntimeError.
- [`test_r3_migration.py`](../../backend/tests/integration/test_r3_migration.py):
  recorrido desde vacío y R2 a R3; aborto con ejecuciones o con ejecuciones y
  métricas relacionadas; rollback ante una vista dependiente; retazos existentes
  conservados; constraints; ambas FK del ciclo; material propuesto sin consumo.
  Compara esquema y datos de las tablas preservadas y los OID de EJECUCION,
  METRICA, sus PK y la FK/UNIQUE de METRICA para detectar recreaciones.
- La comparación completa del ORM vigente con el esquema migrado corresponde
  ahora a R3. `test_database_structure.py` espera las doce tablas actuales.

La integración utiliza PostgreSQL 18.6 temporal y aislado, con datos sintéticos.
No se consulta Supabase ni se aplica allí ninguna revisión. Los upgrades de
pytest solo afectan a las bases temporales del clúster propio. No se ejecutan
los comandos Alembic downgrade/stamp ni seed.

Resultado local R3 con PostgreSQL **18.6**:

```text
159 passed in 70.87s (0:01:10)
```

Sin errores ni omisiones: 113 pruebas anteriores adaptadas y 46 nuevas
(9 unitarias y 37 de integración R3). El esquema migrado coincide con el ORM.
El clúster propio se detuvo al terminar. Se comprobó además que las ocho clases
fuera del cambio permanecen idénticas a R2 y que el snapshot R1 conserva el
contenido del commit de origen. `git diff --check` no presenta incidencias.

`alembic history` (lectura local, código 0):

```text
f2b3c4d5e6a7 -> a3c4d5e6f7b8 (head), R3: trazabilidad de optimizaciones, ejecuciones y material propuesto.
e1a2b3c4d5f6 -> f2b3c4d5e6a7, R2: alinear CONFIGURACION con snapshots del modelo v1.1.
c4e8a1f2b3d5 -> e1a2b3c4d5f6, R1: alinear identidad, inventario y pedidos con el modelo v1.1.
9b9f04eb67f6 -> c4e8a1f2b3d5, HU-003: agregar dni y usuario a usuarios; correo pasa a opcional
<base> -> 9b9f04eb67f6, crear esquema inicial
```

`alembic heads` (lectura local, código 0):

```text
a3c4d5e6f7b8 (head)
```

Esta evidencia acredita la ejecución local aislada; no afirma que Supabase esté
en R3 ni que sus tablas continúen vacías. La aplicación remota queda fuera de
esta fase y requiere cumplir las precondiciones y coordinar el despliegue.
