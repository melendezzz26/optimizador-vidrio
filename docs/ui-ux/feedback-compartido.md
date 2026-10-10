# Mensajes de feedback compartidos — TA-034

Alcance: componentes compartidos de feedback para Users, Inventory y Orders,
conforme a [SPEC-EN-006](../specs/SPEC-EN-006-ui-componentes-compartidos.md) y a la
sección 2.9 de [ADR-002](../adr/ADR-002-operacion-pre-raster.md).
No es un módulo nuevo: los componentes viven en `frontend/src/shared/components/feedback/`
y los módulos existentes los reutilizan.

Estado del diseño: aprobado por el equipo el 08/10/2026.

## Catálogo

| Tipo | Uso | Accesibilidad |
|---|---|---|
| Mensaje de resultado: éxito, error, advertencia, información | Después de una acción, arriba del listado o del formulario | `role="alert"` para error; `role="status"` para los demás |
| Error de campo | Debajo del control con el dato inválido | `aria-invalid` en el control y `aria-describedby` hacia el mensaje |
| Carga | Mientras llegan datos o se envía un formulario | `role="status"`; botón con `aria-busy` y deshabilitado para evitar doble envío |
| Estado vacío | Listado sin datos o sin resultados para los filtros | Explica por qué está vacío y qué acción seguir |
| Confirmación | Acciones con consecuencias, como desactivar | `role="alertdialog"`; foco inicial en Cancelar; Escape cancela |
| Acción deshabilitada | Botón que aún no se puede usar | Texto visible que explica qué falta, asociado con `aria-describedby` |

## Reglas

- Solo se usan los tokens aprobados en la línea base UI/UX v1.0; no se agregan colores.
- Cada mensaje lleva un título escrito; el color y el ícono nunca son la única señal.
- El texto indica qué pasó y qué hacer; no muestra códigos, SQL ni detalles técnicos.
- Los mensajes permanecen visibles hasta la siguiente acción; no desaparecen solos.

## Decisiones pendientes de la paleta

- Advertencia: usa Brand Blue (#61A3E7) y se distingue por ícono y título, porque no existe un token ámbar aprobado.
- Botón de peligro: usa Error (#B91C1C); la variante `danger` figura en el documento UI/UX y se agrega a `ui.css` en esta tarea.

## Patrón de gestión (TA-034 T02)

`frontend/src/shared/hooks/useManagementView.js` implementa el flujo
"listado primero, formulario bajo acción". No dibuja nada: cada módulo
conserva su propio listado y formulario.

| Estado | Qué se muestra |
|---|---|
| `list` (inicial) | Listado, búsqueda, filtros y el mensaje de resultado |
| `create` | Formulario de alta |
| `edit` | Formulario de edición con `editingItem` |

Aplicación: HU-003 T05 (Users) y HU-013 T01 (Orders). Inventory ya cumple el
patrón con su propia implementación y no se reestructura en esta tarea.

Ejemplo de uso:

```jsx
const view = useManagementView();

{view.feedback && (
  <FeedbackMessage variant={view.feedback.variant}>{view.feedback.message}</FeedbackMessage>
)}
{view.isListVisible && (
  <>
    <button className="ng-button ng-button--primary" type="button" onClick={view.openCreate}>
      Nuevo usuario
    </button>
    <UsersTable onEdit={view.openEdit} />
  </>
)}
{view.isFormOpen && (
  <UserForm
    editingUser={view.editingItem}
    onCancel={() => view.backToList()}
    onSaved={(message) => view.backToList({ variant: 'success', message })}
  />
)}
```