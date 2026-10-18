# SPEC-HU006 — Gestión y Registro de Nuevo Pedido con Piezas Estándar y Personalizadas

## Información general

| Campo | Valor |
|---|---|
| Estado | Draft |
| PBI relacionado | HU-006 (Incluye T01, T02, T03, T04) |
| Responsable | Luis Anthony Ibañez Herrera |
| Reviewer | Scrum Master |

## 1. Objetivo

Implementar el flujo completo de "Nuevo Pedido" que permita a los operarios registrar solicitudes de vidrio especificando el material y espesor a nivel global, y agregando múltiples piezas (tanto de formas estándar como polígonos convexos dibujados a medida). El objetivo es garantizar una captura de datos precisa en el frontend mediante validaciones estrictas y ventanas modales, y una persistencia transaccional y estructurada en la base de datos PostgreSQL a través de FastAPI.

## 2. Alcance

### Incluye

- **UI/UX:** Interfaz en React (`NuevoPedido.jsx`) para la captura de características globales y lista de piezas dinámica.
- **Catálogo dinámico:** Consumo de la API de inventario para cargar tipos de vidrio y filtrar espesores.
- **Formas estándar:** Ingreso de medidas paramétricas para formas `RECTANGULO` (ancho, alto) y `CIRCUNFERENCIA` (radio).
- **Formas personalizadas:** Integración del componente `CustomPieceEditor.jsx` como ventana modal superpuesta para dibujar polígonos convexos, capturando vértices exactos e implementando retención de memoria (`rawState`) para ediciones posteriores.
- **Transformación de datos:** Limpieza y aplanamiento de la estructura JSON en el frontend (extracción de atributos al nivel raíz y eliminación de memoria gráfica) para coincidir con los esquemas Pydantic.
- **Backend y Base de Datos:** Endpoint POST en FastAPI para registrar el pedido y sus piezas bajo una única transacción en PostgreSQL, utilizando columnas JSONB para las medidas.

### Fuera de alcance

- Lógicas de optimización de corte de vidrio (nesting).
- Dibujo o validación de polígonos cóncavos o formas con curvas irregulares.
- Gestión de pagos, facturación o estados de envío.

## 3. Actor y precondiciones

**Actor:** Operario del sistema.

**Precondiciones:**

- El operario debe haber iniciado sesión y contar con un token JWT válido (manejado vía `useSession`).
- La API del catálogo de vidrios (`GET /api/inventory/tipos-vidrio`) debe estar en línea y poblar los datos iniciales.
- El esquema relacional en PostgreSQL (tablas `PEDIDO` y `PIEZA`) debe estar creado y operativo.

## 4. Entradas y datos

| Campo / dato | Tipo / formato | Regla |
|---|---|---|
| id_tipo_vidrio | Entero | Obligatorio. Seleccionado del catálogo. |
| espesor_mm | Decimal | Obligatorio. Condicionado al tipo de vidrio. |
| tipo_forma | Cadena (String) | Obligatorio. Valores: `RECTANGULO`, `CIRCUNFERENCIA`, `POLIGONO_CONVEXO`. |
| cantidad | Entero | Obligatorio. Debe ser > 0. |
| width_mm / height_mm | Decimal | Obligatorio solo si la forma es `RECTANGULO`. |
| radius_mm | Decimal | Obligatorio solo si la forma es `CIRCUNFERENCIA`. |
| vertices | Array de Arrays | Obligatorio solo si la forma es `POLIGONO_CONVEXO`. Debe contener ≥ 3 vértices. |

## 5. Reglas de negocio

- **RN-01 (Transaccionalidad):** El registro en la base de datos es atómico. Si una sola pieza falla en la validación o inserción, se ejecuta un rollback total y no se crea el pedido padre.
- **RN-02 (Contrato Plano de Medidas):** El backend no acepta objetos anidados complejos para las medidas. Las cotas (`width_mm`, `height_mm`, `radius_mm`, `vertices`) deben viajar al mismo nivel jerárquico que `tipo_forma` y `cantidad`.
- **RN-03 (Aislamiento de Memoria Gráfica):** El estado interno del lienzo del polígono (`rawState`) es de uso exclusivo del frontend para permitir la re-edición y debe ser purgado antes de enviar el payload a la API.
- **RN-04 (Coherencia Visual):** El botón de "Guardar pedido" permanecerá deshabilitado (`disabled`) hasta que todas las piezas en la lista cumplan con los requisitos de sus respectivas formas.

## 6. Flujo principal

1. El operario ingresa a la vista de "Registro de pedidos".
2. Selecciona un "Tipo de vidrio", lo que habilita la lista desplegable de "Espesores" correspondientes.
3. El operario selecciona el espesor.
4. Hace clic en "Agregar pieza", creando un bloque de configuración.
5. Define la cantidad y selecciona la forma:
   - **Si elige Rectángulo/Circunferencia:** Ingresa las medidas directamente en los campos numéricos de la fila.
   - **Si elige Polígono Convexo:** El sistema abre automáticamente una ventana Modal. El operario dibuja la pieza, asigna medidas a los lados y hace clic en "Agregar pieza al pedido". La ventana se cierra y guarda los vértices en memoria.
6. Una vez completadas y validadas todas las piezas, el operario hace clic en "Guardar pedido".
7. El frontend procesa el payload (aplana dimensiones, elimina `rawState`) y envía un POST a la API.
8. FastAPI valida el payload con Pydantic, abre transacción, inserta el registro maestro, inserta el detalle en formato JSONB y realiza el commit.
9. El sistema muestra un mensaje de éxito, limpia el formulario y restablece el estado inicial.

## 7. Flujos alternativos y errores

- **Error de Validación Frontend:** Si el operario deja una medida vacía o dibuja un polígono incompleto (< 3 vértices), la evaluación `esPedidoValido()` retorna falso y bloquea la acción de guardado.
- **Rechazo de Backend (422 Unprocessable Entity):** Si el payload llega mal estructurado (ej. parámetros extra no permitidos o faltantes), FastAPI devuelve un detalle del error (ej. `Field required` o `Extra inputs are not permitted`). El frontend captura este mensaje y lo muestra en un banner rojo superior (`errorGlobal`).
- **Caída de BD (500 Internal Server Error):** El backend maneja la excepción, revierte cualquier cambio parcial y alerta al operario sobre el error del servidor.

## 8. Criterios de aceptación

- **CA-01:** El formulario permite configurar el tipo de vidrio y espesor global una sola vez, aplicándolo lógicamente a todas las piezas añadidas en esa sesión.
- **CA-02:** El operario puede agregar, re-editar y eliminar múltiples piezas de diferentes formas estándar en una misma vista.
- **CA-03:** El componente `CustomPieceEditor` funciona ininterrumpidamente como un Modal, sin recargar la página, y es capaz de restaurar el dibujo visual si el usuario decide editar un polígono previamente trazado.
- **CA-04:** La API procesa con éxito la petición POST validando mediante Pydantic que los campos dinámicos coincidan estrictamente con el `tipo_forma` indicado.
- **CA-05:** Se pueden registrar pedidos que contengan simultáneamente combinaciones de piezas rectangulares, circulares y polígonos convexos.

## 9. Impacto técnico

### Módulos

- **Frontend:** `src/features/orders/NuevoPedido.jsx` (Lógica principal, armado de payload), `src/features/orders/CustomPieceEditor.jsx` (Lienzo interactivo escalable).
- **Backend:** `routers/orders.py`, `services/order_service.py`, `schemas/orders.py`.

### API

- `GET /api/inventory/tipos-vidrio` (Lectura).
- `POST /api/orders/` (Escritura transaccional).

### Base de datos / migración

- Inserciones DML en tablas `PEDIDO` (cabecera) y `PIEZA` (detalle).
- Almacenamiento paramétrico en el campo `dimensiones` de tipo **JSONB** nativo de PostgreSQL.

### UI

- Rediseño de selectores para soportar múltiples formas.
- Implementación de un Overlay fijo (`z-index: 9999`) para alojar el editor de polígonos, manteniendo la integridad del estado del pedido por debajo.

## 10. Pruebas previstas

- **Unitarias (Backend):** Testeo exhaustivo de Pydantic utilizando inyecciones de payloads inválidos (cantidades negativas, tipos de datos cruzados, estructuras anidadas no permitidas).
- **Integración:** Verificación de la integridad relacional de base de datos simulando fallos a mitad de una transacción para confirmar el rollback.
- **UI/E2E:** Prueba de flujo completo en frontend verificando la habilitación del botón "Guardar" únicamente cuando se hayan dibujado >3 vértices y especificado medidas para todas las filas estándar.

## 11. Evidencias requeridas

- Capturas de pantalla de la UI con un pedido multipieza válido y el Modal de dibujo superpuesto.
- Salida JSON del response 201 de FastAPI confirmando la creación estructurada.
- Consulta SQL en la consola demostrando que las propiedades `width_mm`, `radius_mm` y `vertices` se alojan correctamente en la columna JSONB plana de PostgreSQL.

## Historial de estado

- Draft