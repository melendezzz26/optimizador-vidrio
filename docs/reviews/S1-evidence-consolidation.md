# Sprint 1 — auditoría de consolidación documental

Fecha: **16/10/2026, America/Lima**. Rama única: `chore/S1-final-integration`.
Punto de partida limpio: `cbfa6ad`. Base remota disponible para el PR:
`origin/integration/sprint-01` en `fe79530`.

Este saneamiento modifica exclusivamente documentación/evidencia. No cambia
producto, pruebas, configuración ejecutable del frontend/backend ni migraciones.
Las dos copias de runner/config retiradas estaban dentro de evidencia y fueron
reemplazadas por instrucciones que usan los scripts reales del repositorio.
No se ejecutaron suites ni se reescribieron commits. Sin push ni PR.

## Inventario y decisión por categoría

`S1-OPT-UI/integration` no existe. La integración real a la que apuntan los
documentos está en `S1-OPTIMIZATION-FIRST-FIT/integration`; se auditó ese destino,
los antecedentes UI, `docs/reviews` y todas sus referencias en el repositorio.

| Ubicación de evidencia | Antes | Después |
|---|---:|---:|
| `S1-OPT-UI` | 83 | 12 |
| `S1-OPTIMIZATION-FIRST-FIT/integration` | 267 | 77 |
| Total del ámbito consolidado | **350** | **89** |
| Toda la evidencia de Sprint 1 | 654 | 393 |

Reducción neta del ámbito: **261 archivos (74.6%)**. Se retiran **279 archivos
individuales**, después de comprobar referencias, hash y reemplazo; se incorporan
18 archivos documentales de resultados/expedientes. No se eliminan directorios
recursivamente. El registro de procedencia y este informe están en `docs/reviews`,
fuera del recuento de evidencia. Tamaño del ámbito: aproximadamente 25.93 MB →
8.70 MB (unidades decimales).

| Categoría | Decisión y razón |
|---|---|
| 40 capturas intermedias UI/T1 | Supersedidas por capturas integradas del mismo criterio. Se retienen seis capturas fixture distintas: preparación/resultado raster y círculo sobre retazo en 3D, escritorio/móvil. |
| 55 capturas reales de integración | Todas conservadas: 2D, 3D, progreso, multipedido, multimaterial, unidades físicas, retazo, métricas, confirmación, 409, RBAC, inventario, HU-015 y dashboard. No se alteran imágenes. |
| 31 logs UI y 10 logs de integración intermedia | Reemplazados por resultados finales únicos. Los conteos históricos quedan identificados en README; el baseline backend completo original se conserva en su log. |
| 194 JSON/NDJSON de escenarios | Agrupados en diez expedientes, uno por escenario, con escritorio/móvil separados internamente. Se conservan todos los campos y cada texto NDJSON exacto. |
| Runner/config copiados, manifiesto parcial y resumen viejo | Reemplazados por comandos del producto, manifiesto vigente y resumen final. La copia del runner contenía credenciales sintéticas literales que ya no se conservan en evidencia. |
| OpenAPI y auditoría de ramas/Alembic | Conservados: prueban contrato y procedencia diferentes de las capturas y conteos. |
| README, compatibilidad, grupos/raster, 3D y contrato/RBAC | Conservados y enlazados. Los informes históricos tienen una advertencia de procedencia; no se cambian sus resultados para presentarlos como actuales. |

## Trazabilidad por archivo y criterio

El [registro SHA256](S1-evidence-consolidation-index.json) identifica para cada
archivo retirado: ruta histórica, SHA256 del archivo Windows y del blob Git,
reemplazo vigente y su hash, razón y documentos que lo referenciaban. `source_path` es un **identificador histórico**,
no un enlace activo. Puede recuperarse sin modificar el árbol de trabajo:

```text
git show cbfa6ad:<source_path>
```

Los hashes se calcularon antes de borrar. Las referencias se buscaron en todos
los archivos de texto versionados, dentro y fuera de `docs/`, por ruta absoluta
de repositorio, relativa y nombre de archivo. No se encontró un consumidor de
producto/tests de los archivos eliminados. Las referencias externas a la carpeta
integrada llegan a su README, que permanece. Las referencias de SPEC/PLAN/TASKS
a grupos, 3D y auditorías siguen resolviendo; sus criterios y estados de aprobación
no se modificaron. No se elimina evidencia exclusiva exigida por esos documentos.

Los diez expedientes se compararon contra los **194 archivos originales** antes
de eliminarlos: igualdad estructural para JSON y texto exacto para NDJSON,
incluidos saltos de línea. Por ello siguen disponibles stock antes/después,
resultado confirmado, movimientos, estados, runtimes, ausencia de errores de
navegador y respuestas 409. No se cruzan IDs de bases distintas.

El [índice UI](../evidence/sprint-01/S1-OPT-UI/README.md) mantiene CA01–CA11 y
referencias PBI/SPEC/PLAN/TASKS. La
[matriz real](../evidence/sprint-01/S1-OPTIMIZATION-FIRST-FIT/integration/README.md)
conserva E2E1–10 y su relación con CA-01–28, más HU-015. El
[manifiesto vigente](S1-final-integration-files.txt) enumera únicamente archivos
existentes del diff final contra la referencia remota indicada, incluidos los
nuevos documentos. No enumera bajas históricas como archivos entregados.

## Resultados finales preservados

[Un único índice reproducible](../evidence/sprint-01/S1-OPTIMIZATION-FIRST-FIT/integration/final/README.md)
conserva comandos, entorno, procedencia y limitaciones:

- Backend completo previo: **1976 passed, 1 warning**.
- Orders focalizado previo: **163 passed**, según el estado validado por el equipo;
  no se inventa un log de esa ejecución.
- Optimization backend posterior: **379 passed, 1 warning**.
- Frontend: **159 unit, 453 component, 86 E2E**, sin fallos ni skips.
- Lint: **0 errors, 0 warnings**; build **OK**.
- Alembic: única head **`s1opt02b4c6d`**; migraciones intactas.

Unit/lint/build y Optimization usan salidas reales de la sesión funcional previa;
component/E2E usan reportes estructurados que conservan todos los casos, estados,
duraciones y viewports aplicables. Los SHA256 de sus fuentes están registrados.
Se normaliza codificación y se excluye ruido repetido, configuración personal y
userinfo de una URL sintética en un nombre de prueba. No se cambian resultados.

Las capturas anteriores a Orders se identifican por su entrega real `70a6c36`,
código `c5baa8a`; la corrida E2E final corresponde al código `e1faf3e` y su punto
documental `cbfa6ad`. Los timestamps UTC se interpretan en America/Lima. Esta
consolidación no renombra la corrida histórica de 85 E2E + 1 skip como si fuera
la corrida final de 86 sin skips.

## Referencias, credenciales y comprobaciones de cierre

La revisión documental comprueba enlaces locales, menciones de rutas retiradas,
coherencia de los manifiestos y contenido sensible. Las rutas retiradas solo
permanecen como identificadores explícitos del registro de procedencia, no como
referencias activas. Se actualizan los README raíz/documentación/evidencia para
que conduzcan al cierre integrado y no describan First Fit como excluido.

La revisión de secretos busca valores JWT, tokens de proveedores, claves privadas,
contraseñas, URLs con userinfo y valores de cookies/Authorization. Las menciones
de nombres de variables o campos sin valor no son credenciales. Se retiraron el
runner con contraseñas sintéticas y los logs supersedidos que mostraban una URL
con userinfo usada en un test. No se copian esos valores al registro SHA256.

Se revisa texto de toda `docs/evidence` y `docs/reviews`, más OCR de las imágenes
retenidas. Las capturas del ámbito conservan sus hashes originales; el formulario
de logout muestra campos vacíos. La reproducción remite a las cuentas sintéticas
definidas en el servidor de pruebas, sin valores de contraseña en documentación.

Comprobaciones documentales completadas:

- **0 enlaces locales rotos** en los documentos modificados y los destinos del ámbito auditado.
- **0 referencias activas a rutas eliminadas** en todo el texto versionado del repositorio; se exceptúan únicamente los identificadores históricos del registro de procedencia.
- **167 archivos vigentes** en el manifiesto contra `origin/integration/sprint-01`, frente a 423 del diff inicial.
- **0 cambios fuera de documentación**; SPEC/PLAN/TASKS y migraciones sin cambios durante este saneamiento.
- **194 contenidos JSON/NDJSON** cotejados y preservados; **61 capturas del ámbito** con SHA256 idéntico al original.
- Búsqueda de valores sensibles en **233 archivos de texto** de toda `docs/evidence` y `docs/reviews`: **sin hallazgos**. Se decodificaron las salidas finales UTF-16LE antes de normalizarlas.
- OCR de **165 imágenes** de toda la evidencia: **0 fallos de lectura, sin hallazgos de valores sensibles**. Los nombres de campos de acceso no constituyen contraseñas; el logout se revisó visualmente con campos vacíos.
- `git diff --check`: **OK**.

No se detectaron tokens, contraseñas literales, URLs con credenciales ni valores de cookies o cabeceras de autenticación en la evidencia retenida. No se atribuyen nuevas pruebas funcionales a estos controles.
