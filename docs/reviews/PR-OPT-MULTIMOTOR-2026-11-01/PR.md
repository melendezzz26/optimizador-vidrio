# feat(optimization): integrar comparación visual supervisada FF/BF/WF

Base: `integration/sprint-01` · Rama: `feature/optimization-multimotor-visual`.
Borrador local; PR todavía no creado. Revisión cruzada y CI remoto del futuro
commit final pendientes.

## Problema y comportamiento resultante

La selección de pedidos necesita comparar FF, BF y WF sobre una misma instancia,
con resultados independientes que puedan consultarse y confirmarse de forma
explícita. Esta integración ejecuta los tres motores bajo supervisión, persiste
cada resultado y presenta sus fases y distribuciones reales en pestañas separadas,
además de una tabla comparativa. Seleccionar o simular conserva inventario;
confirmar consume exclusivamente el resultado elegido, de manera transaccional
e idempotente.

## Alcance

- Coordinador, tres procesos `spawn`, presupuestos individuales y acumulados,
  exclusión de cargas incompatibles y limpieza de workers.
- Snapshots/codec con identidad de método, persistencia y recuperación por
  ejecución, selección versionada y API `comparison-v1`.
- Migración Alembic `s2cmp01a1b2c` para metadatos comparativos; contratos y pruebas
  de migración actualizados. No se ejecutan migraciones sobre la base compartida
  como parte de esta preparación.
- Pestañas FF/BF/WF/Comparación, máscaras, orden y avance visual observado,
  solicitud original, vistas 2D/3D, selección y confirmación.
- Pruebas diferenciales, API/PG real, regresiones de persistencia/confirmación,
  supervisor y E2E desktop/móvil. Guía de ejecución Linux/WSL2 y evidencias.

Las políticas FF/BF/WF, geometría, rasterización, rotación y métricas existentes
se reutilizan. El cambio de dominio respecto de integración agrega el hecho
visual `ordering_ready`; no introduce una nueva política de búsqueda.

## Regresiones corregidas y causas

- **RESULT_SAVE_FAILED:** la autorización retenía una conexión de lectura mientras
  el endpoint solicitaba otra para su UoW. Bajo carga agotaba el pool. El guard
  RBAC libera la transacción de lectura antes del repositorio; conserva las
  decisiones de permisos y la propiedad de la sesión. Valores predeterminados
  explícitos: pool 5, overflow 0, sin ampliar cuota del proveedor. Se correlacionan
  comparación/ejecución/método al registrar un fallo de guardado.
- **Reinicios del servidor:** Uvicorn observaba scripts y artefactos de validación.
  El launcher estable desactiva reload por defecto y excluye esos árboles al
  activarlo. Los resultados persistidos sobreviven; los buffers visuales son
  temporales y pueden responder 410 tras reiniciar.
- **Estado residual después de confirmar:** selección, resultados y recuperación
  automática podían restaurar el lote anterior. El controller invalida solicitudes
  anteriores, limpia estado/almacenamiento y refresca pendientes; la pantalla
  vuelve al selector con éxito visible y foco. Un error conserva el contexto.
- **503 en Windows nativo:** el supervisor requiere procfs, RLIMIT_AS y prctl.
  Se documenta WSL2 y se mejora el diagnóstico; se mantienen todos los controles.
  No se añade un fallback de cálculo sin límites.

El 409 angular provenía de configuración histórica de 90°. La base de pruebas
autorizada ya publicó una versión vigente a 5° en una intervención anterior.
Este PR no cambia parámetros remotos ni incluye seeds/UPDATE para activarlos.
Una instalación debe tener esquema compatible y configuración vigente de 5°.

## Evidencia de políticas y resultados

- Contraejemplo mínimo: A=1000×700, B=700×500, pieza=600×400, A primero;
  FF selecciona A, BF selecciona B y WF selecciona A. Verificado por API y UI real.
- Coincidencias legítimas y diferencias completas verificadas en diez casos,
  incluyendo TA-027 pequeño/mediano/complejo, triángulos y figuras mixtas.
- La revisión privada de casos reales confirma coincidencias legítimas FF/BF.
  La evidencia pública usa exclusivamente fixtures sintéticos, incluidos los
  casos WF-15/WF-16. TA-019 compara capacidad libre posterior dentro del primer
  nivel factible, sin prioridad adicional de planchas abiertas; no se cambió
  WF para disminuir artificialmente el número de planchas.
- Oráculos de pruebas independientes contrastan áreas, rotación, bits de
  colocación, margen/separación, recuperables y métricas; el E2E contrasta los
  contornos 2D/3D contra el DTO real. Las mutaciones de pruebas usan PG aislado.

## Validación local registrada

| Grupo | PASS | FAIL | SKIP |
|---|---:|---:|---:|
| Backend general | 2471 | 0 | 0 |
| Supervisor, proceso pytest independiente | 14 | 0 | 0 |
| Frontend unitarias | 175 | 0 | 0 |
| Frontend componentes | 526 | 0 | 0 |
| E2E del repositorio, desktop/móvil | 126 | 0 | 0 |
| Recorridos UI adicionales de evidencia | 2 | 0 | 0 |

Lint, build y `git diff --check`: PASS. Los casos focalizados son subconjuntos,
no se vuelven a sumar. Python 3.11.9, Ubuntu WSL2 y PostgreSQL 18 efímero.
El CI conserva dos comandos backend para comprobar el RSS real del supervisor
en un proceso pytest fresco, sin omitir su suite ni aumentar presupuestos.

El gate E2E se evaluó posteriormente con su función real sobre el reporte local:
13 specs críticos exitosos en ambos proyectos, sin skips. No estaba activa la
variable del gate durante esa ejecución local; esto no se presenta como un CI
remoto aprobado. La colección histórica de 2068 se contrastó por node IDs:
2067 conservados y una prueba de configuración reemplazada por otra ampliada.

## Limitaciones y condiciones antes del merge

- Linux/WSL2 y un proceso web: la admisión actual es local al proceso. Windows
  nativo y escalado multiproceso requieren adaptadores/coordinación posteriores.
- Una fuente compatible fuera del límite raster puede invalidar el cálculo aun
  con otra fuente utilizable: 201 seguido de fallo y liberación de pedidos,
  inventario intacto, mensaje genérico. Diagnóstico registrado; no se amplían
  límites ni se omiten fuentes silenciosamente.
- Permanecen pendientes UI/UX de contraste, foco y formato de métricas;
  no se declara conformidad WCAG AA. WF puede ofrecer soluciones dispersas.
- Advertencias existentes: chunk de build >500 kB y deprecación TestClient/httpx.
- Pendientes: revisar el diff final/migración y las correcciones RBAC con otra
  persona, ejecutar CI del commit final y resolver o acordar el tratamiento de
  las deudas conocidas. Esta preparación no constituye autorización de merge.

## Aceptación funcional pendiente antes del merge

- [ ] Recorrido de aceptación del usuario con varios pedidos: selección,
  cantidades expandidas, resultados, confirmación e historial.
- [ ] Mensajes y estados cuando no hay stock compatible: no presentar una
  distribución vacía como una optimización exitosa.

Estos puntos permanecen pendientes; las pruebas técnicas existentes no se
presentan como aceptación del usuario. Si se confirma una regresión introducida
por la integración, deberá corregirse y validarse antes de autorizar merge.
La visualización interactiva futura de separación queda fuera de este PR.

## Trazabilidad

- [SPEC](https://github.com/melendezzz26/optimizador-vidrio/blob/feature/optimization-multimotor-visual/docs/specs/SPEC-OPT-MULTIMOTOR-VISUAL.md) y
  [PLAN](https://github.com/melendezzz26/optimizador-vidrio/blob/feature/optimization-multimotor-visual/docs/specs/PLAN-OPT-MULTIMOTOR-VISUAL.md).
- [Auditoría final A–I y comandos](https://github.com/melendezzz26/optimizador-vidrio/blob/feature/optimization-multimotor-visual/docs/evidence/sprint-02/OPT-MULTIMOTOR-VISUAL/FINAL-AUDIT-2026-11-01/README.md).
- [Casos y métricas](https://github.com/melendezzz26/optimizador-vidrio/blob/feature/optimization-multimotor-visual/docs/evidence/sprint-02/OPT-MULTIMOTOR-VISUAL/FINAL-AUDIT-2026-11-01/CASE-RESULTS.md).
- [Persistencia, pool y UX](https://github.com/melendezzz26/optimizador-vidrio/blob/feature/optimization-multimotor-visual/docs/evidence/sprint-02/OPT-MULTIMOTOR-VISUAL/FF-PERSISTENCE-UX-2026-11-01/README.md).
- [Guía WSL2](https://github.com/melendezzz26/optimizador-vidrio/blob/feature/optimization-multimotor-visual/docs/development/optimization-wsl2.md).

No se modificó inventario ni configuración de Supabase durante las auditorías
de transacciones/preparación. No se incluyen snapshots privados, credenciales,
entornos, clústeres temporales, cachés ni logs brutos de operación.

- [x] Verificación local registrada y evidencias reproducibles.
- [x] Políticas existentes conservadas; tres resultados independientes.
- [x] Inventario y confirmación probados en PostgreSQL aislado.
- [ ] Revisión cruzada humana del conjunto final.
- [ ] CI remoto del commit final.
- [ ] Autorización de merge por el equipo.
