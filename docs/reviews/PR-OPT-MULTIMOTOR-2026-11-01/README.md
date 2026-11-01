# Propuesta de archivos y commits — 01/11/2026

Preparación local y ejecución autorizada de cuatro commits, sin publicación. Base:
`integration/sprint-01` (`afd5f85f9dd1495e4237e1029555f7e56cd53f30`); rama:
`feature/optimization-multimotor-visual`, HEAD
`5e836cdd9cc61eb212402d90dbe94a6776afcc75`. Se conservarán los 23 commits propios
ya existentes; no se propone rebase, squash local ni reescritura de historia.
Las referencias remotas se comprobaron con `git ls-remote` durante la preparación
anterior. Esta entrega opera exclusivamente en la rama local: no hace push,
no crea PR remoto y no modifica referencias remotas.

## Archivos exactos

Propuesta: **136 rutas pendientes** (130 previas + seis documentos nuevos),
**239 rutas en el PR completo** contra integración. La historia existente ya
modifica 115 rutas; parte de ellas también recibe correcciones pendientes,
por lo que estos conteos no se suman entre sí.

- [include-pending.txt](include-pending.txt): allowlist literal de los cambios
  pendientes y estos documentos de preparación, una ruta por línea. Es la
  selección para los futuros commits, no todo el árbol del repositorio.
- [include-pr.txt](include-pr.txt): diff completo previsto contra integración,
  incluyendo implementación ya comprometida y cambios pendientes.
- [commit-plan.json](commit-plan.json): asignación exacta archivo→commit
  local autorizado, con hashes del contenido fuente. Estos documentos de preparación
  se identifican como metadatos; no se intenta autorreferenciar su propio hash.
- [exclude.json](exclude.json): exclusiones explícitas y reglas. Ninguno de los
  130 archivos pendientes auditados necesita descartarse. Los privados/locales
  ya están ignorados y no se borran del disco.
- [PR.md](PR.md): título y descripción listos para revisión; no se creó un PR.

La selección preserva los siete casos adicionales y los tres originales TA-027,
el spec `optimization-policy-audit.spec.js`, su registro crítico, los 14 casos
del supervisor y los dos comandos backend de CI. Incluye los arreglos de
conexiones/RBAC, confirmación frontend, fixtures de fallo y evidencia asociada.

Los ocho archivos bajo `OPT-MULTIMOTOR-VISUAL/logs/` ya comprometidos se conservan:
son registros normalizados de pruebas sintéticas, relacionados con comandos y
resultados históricos, no logs privados de operación. Quitarlos eliminaría
evidencia verificable. Los logs originales del backend del usuario y salidas
locales sin depurar quedan excluidos bajo `.venv` o fuera del checkout.

## Secuencia de commits propuesta

| Orden | Mensaje convencional | Alcance |
|---|---|---|
| 1 | `fix(optimization): estabilizar persistencia y supervisión local` | Liberación RBAC antes del UoW, pool acotado, correlación de errores, diagnóstico WSL2/launcher, regresiones backend y dos grupos CI; guía y comandos asociados. |
| 2 | `fix(optimization): limpiar el flujo tras confirmar una distribución` | Estado/peticiones tardías, recuperación, refresco de pendientes y foco; componentes y E2E de confirmación/Dashboard afectados. |
| 3 | `test(optimization): demostrar políticas FF BF WF y geometría real` | Fixtures y oráculos, diez experimentos API, cinco diagnósticos de capacidad, E2E 2D/3D y registro crítico. |
| 4 | `docs(optimization): registrar auditoría final y preparación del PR` | Evidencias WSL2/configuración/persistencia/UX/final y esta propuesta, sin cambiar retrospectivamente sus resultados. |

Archivos por commit: **19 / 8 / 6 / 103**, respectivamente. La asignación literal
está en `commit-plan.json`; todas las rutas pendientes aparecen una sola vez.

Son cuatro commits **nuevos al final** de la historia existente. Se asignan
archivos completos, sin dividir a ciegas hunks de tests compartidos. El JSON
documenta las dependencias: backend/fixtures antes del E2E y fixtures
diferenciales junto con los tests que los importan.

## Comprobación del staging propuesto

Se usa un índice y almacén de objetos **temporales**, bajo
`backend/.venv/validation/pr-preparation/`. `git read-tree HEAD` inicializa ese
índice y `git add --pathspec-from-file` incorpora exclusivamente las rutas del
allowlist de cada grupo, sin `git add .` ni forzar ignorados. Se comprueban
diffs por grupo, conjunto completo contra HEAD y contra integración,
`--check`, códigos/métodos críticos, hashes auditados y patrones sensibles.

El resultado mecánico de la preparación queda exclusivamente en validación
local ignorada; no se ofrece como enlace público. No representa otra ejecución
de las suites. La fase temporal conservó el índice real. La fase autorizada
usa staging explícito por grupo, comprueba lista y whitespace antes de cada
commit, conserva los 23 commits previos y deja el índice vacío al terminar.
Los objetos temporales y originales privados no se incluyen en los commits.

Resultado de la comprobación:

| Comprobación | Resultado |
|---|---|
| 130 archivos previos frente al manifiesto | PASS antes de anonimizar; después solo cambian los documentos/hashes autorizados. |
| Selección de cada grupo y del PR completo | PASS; coincide exactamente con ambos allowlists, sin omisiones ni rutas adicionales. |
| `git diff --check` por grupo y contra integración | PASS. |
| Código probado frente a 573 hashes registrados | PASS; no se reejecutan ni se inventan pruebas en esta preparación documental. |
| Supervisor, dos comandos CI, diferencial y spec E2E crítico | Incluidos. |
| Índice real, HEAD y rama | Preparación temporal sin cambios; cuatro commits locales autorizados en la misma rama. |
| Patrones sensibles | Solo la URL ficticia localhost conocida de `test_config.py`; valores privados no exportados. |
| Entornos, cachés, bases y datos privados | Fuera de ambos allowlists; no se borran archivos. |

## Procedencia, alcance y revisión documental

El manifiesto de la auditoría cubre sus 232 archivos más su propio JSON
(excluido de autorreferencia): 233 rutas del diff previsto anterior. Los 130
pendientes coincidían en contenido al iniciar esta preparación. Estos seis
documentos nuevos se añaden como propuesta revisable; no alteran implementación,
tests ni resultados de pruebas auditados.

### Anonimización autorizada antes de los commits

El informe final público se corrigió para retirar identificadores operativos,
áreas de inventario y scores derivados de casos privados. Se mantienen las
conclusiones técnicas y todos los fixtures sintéticos reproducibles; no se
reemplazan datos privados por cifras inventadas. El contenido anterior se
conserva únicamente en validación local ignorada. Se actualizan sus hashes y
los manifiestos de preparación; los 573 hashes de código probado permanecen
intactos. Los resultados históricos de pruebas no se alteran.

La descripción del futuro PR utiliza enlaces absolutos a documentos que
pertenecen al árbol local previsto. Su disponibilidad remota solo podrá
comprobarse después de un push autorizado; esta entrega no lo ejecuta.

Se conservan los 103 archivos documentales: contratos/trazabilidad y guiones,
JSON de decisiones/máscaras y colecciones históricas exigidos por la auditoría,
y capturas por estado/rol/escritorio/móvil. Un par de capturas idénticas
documenta dos pasos distintos del recorrido y conserva sus referencias.
No se incorporan logs de operación ni snapshots remotos.

El diff contra integración conserva solo la integración comparativa y sus
regresiones/evidencias. Cambios transversales justificados: liberación de
lecturas RBAC (también Inventario/Dashboard), expectativas de head Alembic por
la nueva revisión comparativa y `minmax(0,1fr)` para el reflow móvil del editor
usado por el flujo. No se incorpora M4/M5/M6 ni un rediseño UI transversal.

SPEC/PLAN distinguen la autorización de diseño/desarrollo por el usuario de
la revisión cruzada y CI remoto, ambos pendientes. Las cifras anteriores en
evidencia histórica se conservan vinculadas a sus revisiones; los resultados
actuales son 2485 backend, 175 unitarias frontend, 526 componentes, 126 E2E del
repo y dos recorridos adicionales. No se declara que las suites se volvieron
a ejecutar al preparar archivos; los hashes contrastan el código ya probado.

## Condiciones pendientes antes del merge

1. Los cuatro commits están autorizados solo localmente; cualquier push y
   creación del Draft PR requieren autorización posterior.
2. Revisión cruzada del PR y CI remoto del commit final, incluyendo ambos grupos
   backend y los 13 specs críticos E2E en escritorio/móvil.
3. Revisión de la migración comparativa y de la liberación de lectura RBAC;
   ninguna migración, seed ni publicación angular se ejecuta aquí.
4. Mantener Linux/WSL2, un proceso web y los presupuestos actuales. Los límites
   de fuentes grandes y los mensajes asociados permanecen como pendiente
   separado; no omitir fuentes ni subir raster para hacer pasar cargas.
5. El reviewer debe conocer las deudas de contraste/foco/formato, buffers visuales
   temporales y dispersión legítima de WF. No se declara conformidad WCAG AA ni
   autorización de despliegue/merge.

6. Recorrido de aceptación del usuario con varios pedidos y revisión de mensajes/
   estados sin stock compatible, evitando presentar una distribución vacía como
   optimización exitosa. Ambos puntos permanecen pendientes; una regresión
   confirmada de la integración bloqueará el merge. La visualización interactiva
   futura de separación pertenece a otro trabajo.

Esta entrega crea únicamente los cuatro commits locales autorizados. No hace
push, PR remoto, merge, rebase, despliegue ni escrituras en Supabase.
