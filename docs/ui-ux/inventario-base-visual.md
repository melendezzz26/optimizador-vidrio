# Base visual de Inventario — HU-004

Alcance: presentación de [RegistrarPlanchaForm](../../frontend/src/features/inventory/RegistrarPlanchaForm.jsx)
y composición desacoplada en [RegistrarPlanchaPage](../../frontend/src/features/inventory/RegistrarPlanchaPage.jsx),
conforme a [SPEC-HU-004](../specs/SPEC-HU-004-registrar-plancha.md).
Referencia consultada: `Documento_Diseno_UI_UX_Accesibilidad_NewGlass_v1_0.docx`
(documento local del equipo, secciones 5–10).

## Composición y reutilización

En `frontend/src/shared/components/`:

- `AppShell`: sidebar y contenido principal, enlace para saltar al contenido,
  `fondo-vidrio.png` con overlay claro y ancho máximo de 1040 px.
- `Sidebar`: identidad NewGlass y módulos informativos; el módulo activo tiene
  borde, fondo, tipografía resaltada y `aria-current`. No hay enlaces ni
  navegación simulada. Ancho de escritorio: 240 px.
- `PageCard`, `PageHeader`, `ActionBar` en `PageLayout.jsx`: superficie, contexto,
  título y acciones. `PageCard` permite conservar el elemento nativo `form`.
- `ui.css`: secciones mediante `fieldset`/`legend`, grid, campos y botones nativos.
- `tokens.css`: colores, tipografía, espaciados y radios bajo `.ng-ui`.
  No redefine `:root` ni modifica los estilos de otras features.

HU-005 podrá reutilizar esa composición y las clases `ng-form-section`,
`ng-field-grid`, `ng-field`, `ng-control` y `ng-button` con su propio formulario.
No se implementan campos, reglas ni flujos de retazos.

## Montaje posterior

`App.jsx` conserva el flujo actual: comprobar sesión → Login o SessionBar y
NuevoPedido. No existe un selector de módulos; la nueva página no está montada
en ese flujo ni es accesible mediante una ruta nueva.

Cuando exista navegación autorizada, el consumidor autenticado podrá renderizar
`RegistrarPlanchaPage` pasando los mismos `catalogo`, `onSubmit` e `isSubmitting`
del formulario. La sesión y los servicios seguirán siendo responsabilidad del
consumidor. La página ya incluye un elemento `main`; no debe anidarse dentro de
otro `main`. Si el consumidor ya proporciona el shell, puede usar directamente
`RegistrarPlanchaForm` para evitar duplicarlo.

`onCancel` es opcional y se transmite al formulario. Si se omite, Cancelar queda
deshabilitado con una explicación visible. Durante el envío también se bloquea.
No se agregan reseteos, navegación, HTTP ni catálogos de ejemplo.

## Contrato y estados conservados

Sin cambios en el filtrado del catálogo, compatibilidad tipo–espesor, limpieza
del espesor, validaciones, conversión numérica del payload, foco al primer error
habilitado, prevención de doble envío y manejo de promesas/errores.
Se conservan labels, IDs, `aria-invalid`, `aria-describedby` y `aria-busy`.

La presentación incluye catálogo vacío, errores textuales, disabled y
`Registrando...`, junto a un icono que respeta reducción de movimiento.
Sidebar fija en escritorio; a 800 px pasa al flujo normal para dejar espacio
al contenido. A 600 px los campos y las acciones pasan a una columna.

## Cierre de revisión visual — 05/10/2026

El usuario aprobó la revisión visual de escritorio. Antes de retirar el montaje
temporal se verificó la pantalla en Chrome headless, con capturas de página
completa y mediciones del DOM:

| Ancho del viewport | Formulario | Sidebar | Overflow horizontal | Solapamientos entre controles |
|---|---|---|---|---|
| 768 px | Dos columnas | En el flujo superior | No | No |
| 375 px | Una columna | En el flujo superior | No | No |
| 400 px | Una columna | En el flujo superior | No | No |

Los controles y botones miden 44 px de alto. Ambos botones estaban habilitados
en el montaje temporal y sus centros eran alcanzables tras desplazar la página.
Se inspeccionaron visualmente las capturas de 768 y 375 px, sin recortes ni
solapamientos; no se realizaron ajustes de diseño durante este cierre.

Se restauró `App.jsx` a su implementación anterior y se retiraron el catálogo
y los callbacks temporales del frontend. Las referencias a IDs ficticios en
evidencias históricas de HU-004 permanecen como documentación de pruebas previas;
no son datos ni código de la implementación definitiva.

Estas comprobaciones no equivalen a pruebas E2E ni certificación de accesibilidad.
Lighthouse no se ejecutó; TA-011 permanece fuera del alcance.
