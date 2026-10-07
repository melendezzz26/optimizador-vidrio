# HU-005: formulario de retazo

## Objetivo y procedencia

Documentar la implementación y verificación de T01 para el formulario desacoplado de registro de retazos, en relación con la [SPEC HU-005](../../../specs/SPEC-HU-005-registrar-retazo.md).

Los resultados de esta evidencia corresponden a la revisión visual y funcional manual aprobada del formulario.

## Archivos implementados

- Página: [RegistrarRetazoPage.jsx](../../../../frontend/src/features/inventory/RegistrarRetazoPage.jsx).
- Formulario: [RegistrarRetazoForm.jsx](../../../../frontend/src/features/inventory/RegistrarRetazoForm.jsx).

## Contrato y comportamiento

| Elemento | Implementación verificada |
|---|---|
| Catálogo | Recibido mediante la prop `catalogo`; el formulario no realiza HTTP directamente. |
| Envío | Entrega el payload mediante la prop `onSubmit`. La integración React → API corresponde a TA-011. |
| Estado de envío | Recibe `isSubmitting` para controlar el estado de carga. |
| Cancelación | Recibe `onCancel` para el flujo de cancelación. |
| Formas soportadas | `RECTANGULO`, `CIRCUNFERENCIA` y `POLIGONO_CONVEXO`. |

### Geometrías

- `RECTANGULO`: solicita ancho y alto.
- `CIRCUNFERENCIA`: solicita radio.
- `POLIGONO_CONVEXO`: solicita como mínimo tres vértices con coordenadas X/Y. Permite agregar y eliminar vértices, sin reducir la lista por debajo de tres.

### Validación y accesibilidad

Las validaciones se exponen mediante `label`, `aria-invalid`, `aria-describedby` y mensajes próximos al campo. La revisión visual/manual del formulario fue aprobada.

## Verificación técnica

Ejecutada desde `frontend`:

- `npm.cmd run lint`: **PASS**.
- `npm.cmd run build`: **PASS**.

Este documento no afirma que React esté conectado a la API. Esa integración queda fuera de HU-005 y corresponde a TA-011.
