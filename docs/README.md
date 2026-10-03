# NewGlass — Documentación de Ingeniería

Este directorio contiene la documentación operativa y versionable de NewGlass.
La guía común del equipo está en [CONTRIBUTING.md](../CONTRIBUTING.md).

Los documentos formales en Word/PDF utilizados para presentación académica se
mantienen en Notion. El repositorio conserva documentación técnica en Markdown,
diagramas fuente y evidencia seleccionada y reproducible.

## Ubicaciones

| Ruta | Contenido |
|---|---|
| `architecture/` | Diagramas fuente: `data-model.drawio` y `system-architecture.drawio`. |
| `adr/` | Decisiones arquitectónicas; [ADR-001](adr/ADR-001-seleccion-arquitectura.md). |
| `specs/` | SPEC por trabajo, a partir de [SPEC-TEMPLATE.md](specs/SPEC-TEMPLATE.md). |
| `database/` | Documentación de persistencia; [refactor de shared/database](database/refactor-shared-database.md). |
| `seguridad/` | [Matriz de permisos](seguridad/matriz_permisos.md) existente. |
| `infrastructure/` | [Convenciones para entornos y procedimientos](infrastructure/README.md). |
| `ui-ux/` | [Convenciones de documentación de interfaz](ui-ux/README.md). |
| `testing/` | [Ubicación de pruebas y comandos](testing/README.md). |
| `spikes/` | [Investigaciones técnicas](spikes/README.md). |
| `evidence/` | [Evidencia real por sprint e identificador](evidence/README.md). |

Para Sprint 1, la evidencia se ubica en `evidence/sprint-01/<ID>/`. La evidencia
existente de `shared/database` está en `evidence/sprint-01/EN-001/`.
`evidence/sprint-01/SP-001-raster/` está reservado, sin resultados declarados.

Los experimentos ejecutables están fuera de `docs/`, en
[`experiments/raster/`](../experiments/raster/README.md): `cases/` para entradas,
`scripts/` para exploración y `results/` para salidas generadas.
First Fit, Best Fit y Worst Fit quedan fuera del alcance de Sprint 1.

## Flujo documental

`PBI/HU -> SPEC -> implementación -> pruebas -> evidencia -> PR`

Las incertidumbres se investigan mediante spikes y las decisiones arquitectónicas
transversales se registran mediante ADR. Los README de directorios reservados
definen convenciones; no acreditan funcionalidades, pruebas o investigaciones
todavía no realizadas.
