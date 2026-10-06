# SPEC-HU-005 - Registrar retazo

## 1. Información general

| Campo | Valor |
|---|---|
| Estado | Specified |
| PBI relacionado | HU-005 - Registrar retazo |
| Responsable | Equipo de desarrollo |
| Reviewer | Pendiente |
| Épica | EP-001 - Módulo de gestión de inventario |
| Sprint | Sprint 1 |

## 2. Objetivo
Permitir a un usuario con rol de Almacenero registrar un retazo de vidrio reutilizable en el inventario, capturando correctamente sus propiedades geométricas, para que el motor de optimización lo pueda considerar como material de origen en futuros cortes.

## 3. Alcance
- Creación de un componente de interfaz de usuario desacoplado (formulario web) para capturar código, tipo, espesor y geometría del retazo.
- El backend y la persistencia de retazos ya están implementados y operativos.
- **Exclusiones:** La integración React ↔ API definitiva (fetch/axios de guardado y navegación) corresponde a la tarea posterior TA-011. HU-005 no debe acoplar el formulario directamente a la red. Tampoco incluye los flujos de descuento por optimización.

## 4. Actor y precondiciones
- **Actor:** Almacenero o Administrador.
- **Precondiciones:**
  - El usuario debe estar autenticado y tener permisos de escritura sobre retazos (`GESTIONAR_RETAZOS`).
  - El tipo de vidrio seleccionado debe estar activo y existir en el catálogo.

## 5. Entradas/datos
El componente visual capturará y emitirá mediante callbacks (y el esquema `RetazoCreate` en API aceptará) exclusivamente:
- `codigo` (string, max 40 chars, único, **obligatorio**)
- `espesor_mm` (Decimal > 0, **obligatorio**)
- `id_tipo_vidrio` (integer, **obligatorio**)
- `geometria` (objeto JSON discriminado por `type`, **obligatorio**)

Campos explícitamente excluidos del envío por el cliente (asignados por backend):
- `area_mm2`: Calculado internamente.
- `estado`: El backend fuerza `True` (Activo) en la creación.
- `id_ejecucion_origen`: El esquema no lo admite en la creación manual, siendo nulo por defecto (`None`).

Formas admitidas para `geometria`:
- **Rectángulo:** `type = "RECTANGULO"`, requiere `width_mm` y `height_mm` (Decimal > 0).
- **Circunferencia:** `type = "CIRCUNFERENCIA"`, requiere `radius_mm` (Decimal > 0).
- **Polígono Convexo:** `type = "POLIGONO_CONVEXO"`, requiere `vertices_mm` estructurado como un arreglo de al menos 3 tuplas `[x, y]` de tipo Decimal (sin exigir que el primer vértice se repita explícitamente al final para "cerrarlo", esto lo maneja el código base).

## 6. Reglas de negocio
1. **Unicidad:** El `codigo` del retazo no puede repetirse en todo el inventario.
2. **Cálculo de Área:** El área es calculada de forma rigurosa y automática por el backend.
3. **Validaciones Geométricas de Dominio:** Además de la estructura JSON, el dominio valida estrictamente la convexidad del polígono, rechazando figuras cóncavas, colinealidad inválida y auto-intersecciones.
4. **Restricción de Espesores:**
   - La implementación actual del backend (TA-013) exige que la combinación de tipo y espesor exista en la tabla intermedia `tipos_vidrio_espesores`.
   - Dicha tabla **no figura** en el diseño original de BD v1.1 (que consta estrictamente de 12 entidades).
   - **Decisión HU-005:** Consumirá el comportamiento actualmente vigente en código. La discrepancia requiere regularización documental del diseño de Base de Datos en paralelo; HU-005 no modificará el esquema de base de datos para saltarse o arreglar esta restricción.

## 7. Flujo principal (Frontend Desacoplado)
1. El usuario visualiza el componente de "Registrar retazo", que recibe el `catalogo` por propiedades.
2. Selecciona el Tipo de Vidrio y Espesor válido.
3. Ingresa un "Código".
4. Selecciona el "Tipo de Forma". El formulario altera dinámicamente sus sub-campos según la elección.
5. Ingresa las dimensiones correspondientes.
6. Al confirmar, el formulario valida que no haya campos vacíos y ejecuta el callback `onSubmit` con el payload de creación estructurado.
7. El componente entra en estado de carga (bloqueo mediante la prop `isSubmitting`).

## 8. Flujos alternativos y errores
- **Geometría cóncava/inválida:** El dominio lo detectará como error y retornará estado 422.
- **Campos faltantes (cliente):** El formulario deshabilita el envío o muestra mensajes descriptivos.
- **Cancelación:** Si el usuario decide cancelar y existe el callback `onCancel`, se desencadena dicho flujo sin alterar estado.

## 9. Criterios de aceptación
- **T01:** El formulario muestra exclusivamente campos para código, tipo, espesor y geometría. Expone una arquitectura de componente controlada usando props: `catalogo`, `onSubmit`, `isSubmitting`, y opcionalmente `onCancel`. (No invoca axios/fetch directamente).
- **T02:** Persistencia verificable directamente contra el API: Realizar un `POST /api/inventory/retazos` válido, comprobar su guardado efectivo en PostgreSQL, y efectuar un `GET` posterior demostrando que devuelve la idéntica geometría y propiedades (no se exige integración desde React para este criterio).
- **T03:** Pruebas funcionales cubriendo 1 caso válido y al menos 2 inválidos (ej. enviar un polígono cóncavo para comprobar el rechazo del dominio por convexidad, y envío de código duplicado).

## 10. Impacto técnico
### Frontend
- Creación de `RegistrarRetazoForm` puro, apoyado en `HU-004` (RegistrarPlanchaForm) como base arquitectónica.
- Interfaz gráfica para la carga de vértices de polígonos que no requiere un `<canvas>`, simplemente un arreglo manejable de inputs numéricos (x,y).

## 11. Pruebas planificadas
- Pruebas unitarias de renderizado del componente.
- **Caso Inválido de Dominio (API):** Verificación explícita de que un polígono cóncavo (ej. en forma de estrella) retorna 422 y no se guarda.
- **Caso Inválido (API):** Verificación de código omitido o tipo de vidrio/espesor inexistentes retornan error correspondiente (422).

## 12. Evidencias esperadas
- T01: Captura de pantalla del formulario desacoplado y código del componente.
- T02: Evidencia (Logs/Screenshots) del Payload HTTP enviado directamente al API, respuesta 201 y salida de DB/GET.
- T03: Logs de respuesta 422 para polígono cóncavo y código duplicado.

## 13. Historial de estado
- **Draft:** Análisis inicial de factibilidad, endpoints actuales. Descarte de bug JSONB y documentación de discrepancia sobre `tipos_vidrio_espesores`.
- **Specified:** Revisión ajustando el alcance al desarrollo de un formulario React desacoplado. Pruebas de API deslindadas de la integración UI completa (TA-011).
