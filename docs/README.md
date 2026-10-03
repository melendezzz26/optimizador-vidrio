# NewGlass — Documentación de Ingeniería

Este directorio contiene la documentación operativa y versionable del proyecto NewGlass.

Los documentos formales en Word/PDF utilizados para presentación académica se mantienen en Notion. El repositorio conserva únicamente documentación técnica en Markdown, diagramas fuente, resultados reproducibles y evidencias.

## Estructura

- `architecture/`: vistas, diagramas y documentación arquitectónica operativa.
- `adr/`: Architecture Decision Records.
- `specs/`: especificaciones funcionales y técnicas activas.
- `database/`: documentación operativa del modelo y migraciones.
- `infrastructure/`: configuración y decisiones operativas de infraestructura.
- `ui-ux/`: criterios y referencias técnicas de interfaz.
- `testing/`: convenciones y documentación operativa de pruebas.
- `spikes/`: investigaciones técnicas y resultados.
- `evidence/`: evidencia reproducible organizada por Sprint.

## Flujo documental

`PBI / HU -> SPEC -> Implementación -> Pruebas -> Evidencia -> Pull Request`

Las incertidumbres técnicas se documentan mediante Spike.

Las decisiones arquitectónicas transversales se registran mediante ADR.
