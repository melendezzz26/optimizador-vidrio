# SPEC-HU-018 — Importación masiva de piezas desde CSV/XLSX

## Información general

| Campo | Valor |
|---|---|
| ID | HU-018 |
| Nombre | Importación masiva de piezas |
| Tareas | T01 — Definir contrato CSV/XLSX · T02 — Parsear y previsualizar archivo · T03 — Validar filas y estado OBSERVADO |
| Sprint | Sprint 2 |
| Estado | **Draft** |
| Responsable | Fabricio Aguilar |
| Reviewer | Por asignar (distinto del autor) |
| Rama | `feature/S2-HU018-importacion-masiva` |
| Base | `origin/integration/sprint-01` en `f9cfd4f` |
| Fecha | 01/11/2026 |
| Origen | Indicación del docente (sesión Taller 09, 28/10/2026) y asignación del Scrum Master |
| Dependencias | Registro manual de pedidos (HU-006, HU-007, S1-orders-material-flow); validación geométrica existente (`GeometryValidator`) |
| Fuera de este bloque | Pruebas de estrés con 100/150/200 piezas; M4, M5 y M6; TA-044, TA-045, TA-047, TA-049 y TA-050 |

## 1. Objetivo

Que el usuario pueda cargar **muchas piezas a la vez** desde un archivo CSV o XLSX,
ver cómo el sistema interpretó cada fila y corregir las filas con errores antes de
registrar el pedido.

**Historia:** como operario, quiero cargar las piezas de un pedido desde un archivo,
para no ingresarlas una por una cuando son muchas.

El docente lo planteó para alimentar el optimizador de forma masiva (por ejemplo,
100 piezas) y comprobar su comportamiento determinístico: misma entrada, misma salida.

## 2. Alcance

### Incluye

- El formato del archivo (§4), con ejemplos válidos e inválidos (§10).
- Un endpoint de **previsualización** que lee el archivo, valida cada fila y devuelve
  el resultado **sin escribir en la base de datos**.
- En el registro de pedido, la opción **"Importar CSV/XLSX"**: seleccionar el archivo,
  ver la tabla de filas, elegir el material y agregarlas al pedido.
- El estado **OBSERVADO** por fila, con su causa, y el bloqueo de la confirmación
  mientras exista alguna fila observada.
- Pruebas de backend, frontend y un E2E del flujo.

### Fuera de alcance

- Crear el pedido directamente desde el archivo: el pedido se sigue registrando con
  el botón existente del formulario, que conserva todas sus validaciones.
- Editar una fila observada dentro de la tabla de previsualización (ver P-02).
- Pruebas de estrés de 100/150/200 piezas (siguiente bloque).
- Integración con M4, M5 y M6: solo se usan First Fit, Best Fit y Worst Fit.
- Cambios de esquema o migraciones.

## 3. Situación actual (evidencia)

Revisión de `integration/sprint-01` en `f9cfd4f`:

- **Backend** (`orders/presentation/schemas.py`): una pieza es `RECTANGULO`
  (`width_mm`, `height_mm`), `CIRCUNFERENCIA` (`radius_mm`) o `POLIGONO_CONVEXO`
  (`vertices_mm`, al menos 3 vértices). Cada pieza lleva `id_tipo_vidrio`,
  `espesor_mm` y `cantidad` (entero, de 1 a 2 147 483 647).
- **Reglas geométricas** (`orders/domain/geometry.py`): `GeometryValidator` valida
  medidas positivas, área almacenable y que el polígono sea convexo, simple y no
  degenerado. La importación las **reutiliza**; no crea reglas paralelas.
- **Frontend** (`FormularioPedido.jsx`): las piezas se agrupan por material
  (`materialGroups`: tipo de vidrio + espesor). Un polígono se guarda como vértices y
  el editor puede reconstruir su dibujo a partir de ellos.
- **Polígonos por lados y ángulos:** en el registro manual, el operario dibuja la
  figura, escribe las medidas de los lados y puede fijar ángulos interiores. El
  frontend (`angularConstraints.js`, `constrainedGeometry.js`) calcula los vértices
  usando el dibujo como guía y envía solo `vertices_mm`; el backend valida esos
  vértices. Un archivo no tiene dibujo, así que la importación necesita su propia
  construcción de vértices (§4.4, §8.1). No duplica la del editor: resuelve el caso
  sin dibujo, y el resultado pasa por el mismo `GeometryValidator`.
- **Límite existente:** TA-037 L-04 admite hasta 128 vértices por pieza.
- **Dependencias:** `requirements.txt` no incluye librerías para recibir archivos
  (`python-multipart`) ni para leer Excel (`openpyxl`).

## 4. Contrato del archivo

### 4.1 Estructura de cada fila

Cada fila describe **una pieza** en tres partes, separadas por **comas**:

```text
TIPO,CANTIDAD,MEDIDAS
```

| Tipo | Letra | Medidas | Ejemplo |
|---|---|---|---|
| Círculo | `C` | `radio` | `C,2,150` |
| Rectángulo | `R` | `largo,ancho` | `R,3,800,600` |
| Polígono convexo | `P` | `{{lado,ángulo},{lado,ángulo},…}` | `P,1,{{120,60},{160,120},{120,60},{160,120}}` |

- **Unidades:** milímetros (longitudes) y grados (ángulos).
- **Números:** con punto decimal (`12.5`). La coma es el separador, por lo que no se
  admite la coma decimal.
- **Letras del tipo:** se aceptan en mayúscula o minúscula (`r`, `R`).
- **Espacios** alrededor de los valores se ignoran (`R, 3, 800, 600` es válido).
- **Material:** el archivo **no** trae tipo de vidrio ni espesor. Se eligen en la
  pantalla de importación y se aplican a todas las filas de ese archivo (§6.1).

### 4.2 Reglas por tipo

- **Cantidad:** entero mayor que 0.
- **`C`:** exactamente 1 medida, el radio, mayor que 0.
- **`R`:** exactamente 2 medidas, largo y ancho, mayores que 0. No lleva ángulos: son
  siempre de 90°. El largo se guarda como `width_mm` y el ancho como `height_mm`.
- **`P`:** una lista de pares `{lado,ángulo}` envuelta en llaves exteriores, como el
  ejemplo del docente:
  - **lado:** longitud del lado, mayor que 0;
  - **ángulo:** ángulo **interior** al **final** de ese lado, es decir, entre ese lado
    y el siguiente; mayor que 0 y menor que 180 (polígono convexo);
  - **mínimo 3 pares** y **máximo 128** (límite L-04 de TA-037);
  - el ángulo puede quedar **vacío** (`{160,}` o `{160}`): el sistema lo calcula
    (§4.4);
  - por compatibilidad con la asignación del Scrum Master, también se acepta la lista
    sin las llaves exteriores: `{120,60},{160,120},…`.

### 4.3 Lectura de la fila

Las llaves agrupan lados y ángulos al estilo JSON, pero un lector CSV común **no**
las entiende: para él toda coma separa columnas. Por eso la fila no se lee con un
lector CSV estándar, sino así:

1. **Primer valor:** el tipo.
2. **Segundo valor:** la cantidad.
3. **Todo lo que sigue:** las medidas, interpretadas según el tipo. En un polígono se
   validan las llaves y los números se leen **por pares** (lado, ángulo), como indicó
   el docente.

Así el mismo contenido funciona como texto CSV, abierto en Excel (aunque Excel parta
el polígono en varias columnas) o escrito en Excel con las medidas en una sola celda.

### 4.4 Ángulos vacíos en polígonos

El editor de piezas permite fijar **hasta** *n − 3* ángulos y resuelve el resto a
partir del dibujo. Un archivo no tiene dibujo, así que la forma solo queda definida si
hay **al menos** *n − 3* ángulos indicados, donde *n* es el número de lados. Entonces:

| Ángulos vacíos | Resultado |
|---|---|
| 0 (todos indicados) | Se construye el polígono y se comprueba que **cierre** y que los ángulos sumen (n − 2) × 180°. |
| 1 o 2 | El sistema calcula los vacíos y comprueba que la figura cierre. |
| 3 | El sistema calcula los vacíos (la figura queda definida por los lados). |
| Más de 3 | **OBSERVADO:** "Faltan ángulos para definir el polígono". |

En todos los casos, el polígono resultante se valida con `GeometryValidator`
(convexo, simple y con área positiva).

**Tolerancias** (para admitir ángulos redondeados a mano, como 36.87° y 53.13°):

- cierre: la distancia entre el último punto y el primero debe ser ≤ **0.5 mm**, la
  mitad de la resolución raster de 1 mm;
- suma de ángulos: diferencia ≤ **0.1°** con (n − 2) × 180°.

### 4.5 Fila de títulos y filas vacías

- Si la **primera** fila con contenido no empieza con `R`, `C` o `P`, se considera
  **fila de títulos** y se ignora (por ejemplo `tipo,cantidad,medidas`).
- Cualquier otra fila que no empiece con `R`, `C` o `P` queda **OBSERVADO**.
- Las filas completamente vacías se ignoran y no se cuentan como piezas.

### 4.6 Archivos admitidos

| Formato | Regla |
|---|---|
| `.csv` | Texto UTF-8 (con o sin BOM), una pieza por línea. |
| `.xlsx` | Primera hoja. En cada fila se unen las celdas no vacías con comas y se lee igual que una línea CSV. Lo natural es usar 3 columnas: tipo, cantidad y medidas. |

| A | B | C |
|---|---|---|
| R | 3 | 800,600 |
| C | 2 | 150 |
| P | 1 | {{120,60},{160,120},{120,60},{160,120}} |

**Límites de protección**, para que un archivo grande no sature el servidor:
**1 MB** por archivo y **500 filas** con contenido. Por encima, la previsualización se
rechaza completa con un mensaje claro. Otras extensiones (`.xls`, `.txt`, etc.) se
rechazan.

## 5. Estado de cada fila

| Estado | Significado |
|---|---|
| `VALIDO` | La fila se interpretó y cumple todas las reglas; está lista para importar. |
| `OBSERVADO` | La fila tiene uno o más errores; se muestra con sus causas. |

- **Nunca** se descarta una fila con errores ni se reemplazan sus datos por valores por
  defecto. La fila observada se muestra tal como venía (texto original) junto a su
  número de fila en el archivo.
- Una fila puede tener **varias causas**; se muestran todas las que se puedan detectar.

### 5.1 Causas

| Situación | Causa mostrada |
|---|---|
| Primer valor distinto de R, C o P | `Tipo de pieza desconocido` |
| Falta la cantidad o no es un número | `Falta la cantidad` / `Cantidad inválida` |
| Cantidad 0, negativa o decimal | `Cantidad debe ser un entero mayor a 0` |
| Círculo sin radio | `Faltan dimensiones` |
| Radio 0, negativo o no numérico | `Radio inválido` |
| Rectángulo con menos de 2 medidas | `Faltan dimensiones` |
| Rectángulo con más de 2 medidas | `Sobran valores en la fila` |
| Largo o ancho 0, negativo o no numérico | `Largo inválido` / `Ancho inválido` |
| Llaves mal cerradas, pares incompletos o valores no numéricos | `Formato de polígono inválido` |
| Menos de 3 lados | `Un polígono necesita al menos 3 lados` |
| Más de 128 lados | `El polígono supera el máximo de 128 lados` |
| Lado 0, negativo o no numérico | `Lado N inválido` |
| Ángulo fuera de (0, 180) | `Ángulo N inválido: debe estar entre 0 y 180` |
| Más de 3 ángulos vacíos | `Faltan ángulos para definir el polígono` |
| Lados y ángulos que no cierran o no suman lo correcto | `Los lados y ángulos no forman un polígono cerrado` |
| Polígono que no es convexo, se cruza o no tiene área | El mensaje de `GeometryValidator` (por ejemplo `El polígono no es convexo.`) |

## 6. Flujo

### 6.1 Principal

El orden sigue lo indicado por el docente: primero se carga el archivo y **después** se
elige el material.

1. En el registro de pedido, el operario presiona **"Importar CSV/XLSX"**.
2. Selecciona el archivo. El frontend lo envía a la previsualización.
3. El sistema muestra una tabla con: número de fila, tipo de pieza, cantidad, medidas,
   estado y causas. Arriba, un resumen: total de filas, válidas y observadas.
4. Elige el **tipo de vidrio** y el **espesor**, con el mismo catálogo del formulario.
   El material no interviene en la previsualización, porque la geometría no depende de
   él.
5. Si **todas** las filas son `VALIDO` y hay material elegido, se habilita **"Agregar al
   pedido"**. Al presionarlo, las piezas se agregan al formulario dentro de un grupo con
   ese material; si ya existe un grupo con el mismo material, se agregan a ese grupo.
6. El operario revisa el formulario y registra el pedido con el botón existente, que
   aplica todas las validaciones de siempre, incluida la del catálogo de vidrio.

### 6.2 Con filas observadas

- La tabla muestra las filas `OBSERVADO` resaltadas, con sus causas.
- **"Agregar al pedido" queda deshabilitado** e indica cuántas filas hay que corregir.
- El operario corrige el archivo y lo vuelve a cargar.

### 6.3 Errores del archivo completo

| Situación | Respuesta |
|---|---|
| Extensión no admitida | 422: `Selecciona un archivo .csv o .xlsx.` |
| Archivo vacío o sin filas con contenido | 422: `El archivo no contiene piezas.` |
| Más de 1 MB | 413: `El archivo supera el tamaño máximo de 1 MB.` |
| Más de 500 filas | 422: `El archivo supera el máximo de 500 filas.` |
| CSV que no es UTF-8, o XLSX dañado | 422: `No se pudo leer el archivo. Verifica el formato.` |

Los mensajes no incluyen el contenido del archivo ni detalles internos (TA-041).

## 7. Contrato de la API

`POST /api/orders/import/preview`, `multipart/form-data` con el campo `archivo`.
Requiere el permiso `orders.create`. **No escribe en la base de datos.**

```json
{
  "resumen": { "total": 3, "validas": 2, "observadas": 1 },
  "filas": [
    {
      "fila": 2,
      "texto": "R,3,800,600",
      "estado": "VALIDO",
      "tipo_forma": "RECTANGULO",
      "cantidad": 3,
      "medidas": { "width_mm": 800, "height_mm": 600 },
      "causas": []
    },
    {
      "fila": 3,
      "texto": "P,1,{{120,60},{160,120},{120,60},{160,120}}",
      "estado": "VALIDO",
      "tipo_forma": "POLIGONO_CONVEXO",
      "cantidad": 1,
      "medidas": { "vertices_mm": [[0, 0], [120, 0], [40, 138.56], [-80, 138.56]] },
      "causas": []
    },
    {
      "fila": 4,
      "texto": "C,0,150",
      "estado": "OBSERVADO",
      "tipo_forma": "CIRCUNFERENCIA",
      "cantidad": null,
      "medidas": null,
      "causas": ["Cantidad debe ser un entero mayor a 0"]
    }
  ]
}
```

- Para las filas `VALIDO`, `medidas` usa **los mismos campos** que el registro manual
  (`width_mm`/`height_mm`, `radius_mm` o `vertices_mm`). Así el frontend agrega las
  piezas al formulario sin conversiones propias.
- El material no viaja en la previsualización: no cambia la geometría. Se valida al
  registrar el pedido, como hoy.

## 8. Diseño técnico

Sin cambios de esquema ni migraciones. Dependencias según la arquitectura:
Presentation → Application → Domain; Infrastructure implementa la lectura de archivos.

| Capa | Archivo | Responsabilidad |
|---|---|---|
| Domain | `orders/domain/bulk_import.py` | Reglas puras de una fila: tipo, cantidad, medidas y causas (§4, §5). Sin FastAPI ni librerías de archivos. |
| Domain | `orders/domain/polygon_construction.py` | Lados + ángulos interiores → vértices (§4.4). Después se valida con `GeometryValidator`. |
| Application | `orders/application/bulk_import.py` | Caso de uso `PreviewImport`: recibe las filas de texto y devuelve la previsualización. No usa el repositorio. |
| Infrastructure | `orders/infrastructure/spreadsheet_reader.py` | Lee CSV (UTF-8) o XLSX (primera hoja) y entrega filas de texto con su número. Aplica los límites de §4.6. |
| Presentation | `orders/presentation/router.py`, `schemas.py` | Endpoint de §7, permiso `orders.create`, esquemas de respuesta. |
| Frontend | `features/orders/bulkImportModel.js` | Lógica pura: resumen, ¿se puede confirmar?, filas → piezas del formulario. |
| Frontend | `features/orders/BulkImportPanel.jsx` | Archivo, tabla, material y botón "Agregar al pedido", en ese orden. Usa los componentes compartidos de feedback. |
| Frontend | `features/orders/FormularioPedido.jsx` | Botón "Importar CSV/XLSX" y recepción de las piezas importadas. |

### 8.1 Construcción del polígono (§4.4)

Los vértices se calculan recorriendo los lados en sentido antihorario: cada ángulo
interior *A* equivale a un giro de 180° − *A*. Con ángulos vacíos, los lados entre
dos vértices libres forman tramos rígidos; con 3 vértices libres, las cuerdas de los
tramos forman un triángulo cuyos tres lados son conocidos (solución única); con 1 o 2,
los tramos deben cerrar dentro de la tolerancia. Es un cálculo directo y determinístico:
el mismo archivo produce siempre los mismos vértices.

### 8.2 Dependencias nuevas

| Paquete | Para qué | Justificación |
|---|---|---|
| `python-multipart` | Recibir archivos en FastAPI (`UploadFile`). | Requisito oficial de FastAPI para formularios con archivos. |
| `openpyxl` | Leer `.xlsx` en el backend. | Lectura de XLSX pedida en la tarea; se usa en modo solo lectura. |

Son librerías, no capas ni servicios nuevos. Se propone registrarlas en esta SPEC sin
ADR; ver P-03.

## 9. Criterios de aceptación

| CA | Tarea | Criterio |
|---|---|---|
| CA-01 | T01 | La SPEC documenta el formato de R, C y P, la lectura por pares, el material elegido en pantalla y ejemplos válidos e inválidos. |
| CA-02 | T02 | Un CSV válido con rectángulos, círculos y polígonos se previsualiza con tipo, cantidad y medidas correctos en el formato interno existente. |
| CA-03 | T02 | Un XLSX con el mismo contenido produce exactamente la misma previsualización que el CSV. |
| CA-04 | T02 | La previsualización no escribe en la base de datos: el número de pedidos y piezas no cambia. |
| CA-05 | T02 | En el formulario de pedido, "Importar CSV/XLSX" permite cargar el archivo, ver la tabla de filas y después elegir el material, sin registrar el pedido. |
| CA-06 | T03 | Cada caso de §5.1 produce una fila `OBSERVADO` con su causa; ninguna fila se descarta ni se completa con valores por defecto. |
| CA-07 | T03 | Con al menos una fila `OBSERVADO`, o sin material elegido, "Agregar al pedido" está deshabilitado; con todas `VALIDO` y material elegido, las piezas se agregan al grupo de ese material. |
| CA-08 | T02/T03 | Un polígono con ángulos vacíos (hasta 3) se construye igual en cada carga (determinismo); con más de 3 vacíos queda `OBSERVADO`. |
| CA-09 | T02 | Un pedido registrado con piezas importadas se procesa con First Fit, Best Fit y Worst Fit sin errores. |
| CA-10 | T02 | Los errores del archivo completo (§6.3) responden con mensajes claros y sin eco del contenido. |

## 10. Ejemplos

### Válidos

```text
tipo,cantidad,medidas
R,3,800,600
r, 2, 1200.5, 450
C,2,150
P,1,{{120,60},{160,120},{120,60},{160,120}}
P,2,{120,60},{160,120},{120,60},{160,120}
P,1,{{300,90},{200,90},{300,90},{200,}}
P,1,{{300,},{400,},{500,}}
```

- La fila de títulos se ignora.
- El paralelogramo aparece con y sin llaves exteriores.
- El rectángulo como polígono deja vacío el último ángulo, que el sistema calcula.
- El triángulo 300-400-500 no lleva ángulos: tres vacíos, la figura queda definida.

### Inválidos (OBSERVADO)

| Fila | Causa |
|---|---|
| `C,0,150` | Cantidad debe ser un entero mayor a 0 |
| `C,2,-5` | Radio inválido |
| `R,3,800` | Faltan dimensiones |
| `R,3,800,0` | Ancho inválido |
| `X,1,100` | Tipo de pieza desconocido |
| `P,1,{{120,60},{160` | Formato de polígono inválido |
| `P,1,{{100,60},{100,60}}` | Un polígono necesita al menos 3 lados |
| `P,1,{{120,35},{160,35},{120,45},{160,60}}` | Los lados y ángulos no forman un polígono cerrado (los ángulos suman 175°, deben sumar 360°) |
| `P,1,{{100,},{100,},{100,},{100,}}` | Faltan ángulos para definir el polígono |

El cuadrilátero con ángulos que suman 175° es el ejemplo ilustrativo de la sesión con
el docente: sirve para mostrar el formato, pero esa figura no existe.

## 11. Pruebas previstas

- **Dominio (unitarias):** cada regla y causa de §5.1; construcción del polígono con
  0, 1, 2 y 3 ángulos vacíos; tolerancias; determinismo.
- **Infraestructura:** CSV UTF-8 con y sin BOM; XLSX con 3 columnas, con la fila en una
  celda y con el polígono partido en varias celdas; límites de tamaño y de filas.
- **API:** los casos pedidos por el Scrum Master (rectángulos, círculos, polígonos,
  los tres tipos, múltiples cantidades, cantidad y medidas 0 o negativas, campos
  faltantes, tipo desconocido, polígono mal formado, mezcla de válidas y observadas),
  sin escritura en la base de datos y con permiso `orders.create`.
- **Integración con optimización:** pedido registrado con piezas importadas,
  procesado con First Fit, Best Fit y Worst Fit.
- **Frontend (componentes):** botón deshabilitado con observaciones; piezas agregadas
  al grupo correcto; polígono importado abre en el editor.
- **E2E:** archivo válido y archivo con filas observadas, en escritorio y móvil. El
  spec nuevo se agrega a `criticalSpecs.js` (TA-040).

## 12. Evidencia requerida

`docs/evidence/sprint-02/HU-018/`: archivos de ejemplo usados, capturas de la carga
válida, de la previsualización, de filas observadas y de la confirmación bloqueada,
resultados de las pruebas y enlace al PR.

## 13. Decisiones y preguntas abiertas

- **D-01 (decidida con el docente):** separador coma; llaves al estilo JSON para los
  polígonos; lectura por pares.
- **D-02 (decidida):** el material se elige en la pantalla de importación, **después**
  de cargar el archivo, y se aplica a todas sus filas.
- **D-03 (decidida):** ángulos interiores, al final de cada lado; vacíos calculados
  con al menos *n − 3* indicados.
- **D-04 (decidida):** fila de títulos opcional; XLSX en columnas (tipo, cantidad,
  medidas), leído igual que el CSV.
- **P-01:** ¿confirmar la importación debe agregar las piezas al formulario (propuesta,
  §6.1) o crear el pedido directamente? La propuesta conserva todas las validaciones
  del registro actual.
- **P-02:** el docente sugirió poder corregir una fila observada dentro del sistema.
  En este bloque se corrige el archivo y se vuelve a cargar; la edición en la tabla
  podría ser una mejora posterior.
- **P-03:** ¿las dos librerías nuevas (§8.2) requieren ADR o basta con esta SPEC?
- **P-04:** límites de 1 MB y 500 filas (§4.6). Cubren las pruebas de estrés previstas
  (hasta 200 piezas) con margen.

## Historial de estado

| Fecha | Versión | Estado | Cambio |
|---|---|---|---|
| 01/11/2026 | 0.1 | Draft | Borrador: contrato acordado (D-01 a D-04), reglas, causas, API, diseño y pruebas. |