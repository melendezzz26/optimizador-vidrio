# Funcionalidades del frontend

Cada feature agrupa su interfaz, hooks, estado y acceso a API cuando estos sean
necesarios. No se replican las capas `domain/application/infrastructure/presentation`
del backend.

Las carpetas reservadas son `authentication`, `users`, `inventory`, `orders`,
`optimization`, `results` y `configuration`. Sus `.gitkeep` conservan la estructura
en clones nuevos y no representan funcionalidad implementada.

El código reutilizado por varias features puede ubicarse en
[`../shared/`](../shared/README.md). Evitar imports a detalles internos de otra
feature; acordar contratos explícitos cuando exista una necesidad de integración.

El inicio de sesión vive en `authentication/` y expone su contrato en
`authentication/index.js` (formulario, barra de sesión, `useSession` y
`getAccessToken`). NuevoPedido continúa en `src/pages/`.
Cada migración futura debe revisar consumidores y preservar contratos y pruebas.
Consultar [CONTRIBUTING.md](../../../CONTRIBUTING.md).
