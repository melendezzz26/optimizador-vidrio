# SPEC-HU-008 — Stock compatible
| | |
| :--- | :--- |
| **Estado** | Draft |
| **PBI Relacionado** | HU-008 |
| **Responsable** | Luis Ibañez & Andro Quispe |

## 1. Objetivo
Validar que cada pieza individual de un pedido tenga al menos una fuente de material compatible disponible en el inventario (plancha o retazo) antes de permitir el registro del pedido en el sistema. Esto evita iniciar procesos de optimización inviables.

## 2. Alcance
- **Incluye:**
  - Consulta de planchas nuevas y retazos reutilizables filtrados por tipo de vidrio y espesor.
  - Validación geométrica individual de cada pieza utilizando la regla definida en el Spike SP-005.
  - Bloqueo del registro de pedido si una o más piezas carecen de stock candidato.
  - Generación de mensajes de error específicos (HTTP 422) identificando la pieza sin stock.
- **Fuera de alcance:**
  - Simulación de corte y empaquetamiento conjunto del pedido (*bin packing*).
  - Reserva, descuento o alteración del inventario en base de datos.
  - Manejo de piezas con geometrías no definidas o inválidas (cubierto en validaciones previas de la API).

## 3. Actor y precondiciones
- **Actor:** Operario (inicia el registro del pedido) / Sistema (ejecuta la validación).
- **Precondiciones:**
  - El usuario (Operario) ha iniciado sesión y tiene permisos válidos.
  - La base de datos contiene inventario activo (planchas o retazos).
  - El payload HTTP recibido en el endpoint de creación de pedido es estructuralmente válido.

## 4. Entradas / datos
- **Petición (Payload de Pedido):**
  - `id_tipo_vidrio` (Integer): Material del pedido.
  - `espesor_mm` (Float): Espesor del pedido.
  - `piezas` (Array de objetos): Lista de piezas a validar, cada una con `tipo_forma` y `dimensiones`.
- **Datos de Inventario (Consulta a BD):**
  - Entidades `PLANCHA` y `RETAZO` filtradas.

## 5. Reglas de negocio
- **RN-01 (Filtrado de Material):** Las fuentes candidatas de stock deben coincidir exactamente con el `id_tipo_vidrio` y `espesor_mm` del pedido.
- **RN-02 (Disponibilidad):** Las fuentes candidatas deben tener `estado = True`. Para las planchas, adicionalmente `cantidad > 0`.
- **RN-03 (Cabida Geométrica):** Se aplica la regla geométrica formalizada en **SP-005** (evaluación de Bounding Box con rotación de 90 grados).
- **RN-04 (Bloqueo Estricto):** Si existe **al menos una pieza** en el pedido que no cumple la RN-03 frente a todo el stock disponible (planchas y retazos), se rechaza todo el pedido.

## 6. Flujo principal
1. El backend recibe la solicitud POST para crear un nuevo pedido.
2. La capa de aplicación extrae el material y espesor requeridos.
3. El repositorio de inventario consulta la BD y retorna todas las planchas y retazos disponibles (RN-01, RN-02).
4. El servicio de dominio itera sobre cada pieza del pedido.
5. Para cada pieza, calcula su Bounding Box y verifica si cabe en al menos un elemento del stock retornado (RN-03).
6. Si todas las piezas tienen al menos un candidato válido, la validación pasa y el flujo de registro continúa.

## 7. Flujos alternativos / errores
- **E-01 (Stock Insuficiente por Pieza):**
  - Condición: En el paso 5, una pieza no encuentra ningún candidato compatible.
  - Acción: Se interrumpe la iteración, se bloquea el registro y la API responde con un código HTTP 422 (Unprocessable Entity).
  - Respuesta sugerida: `{"detail": "La pieza [Nombre/Índice] no cuenta con material disponible en stock que soporte sus dimensiones."}`.
- **E-02 (Inventario Vacío):**
  - Condición: En el paso 3, la consulta a BD retorna una lista vacía para ese material/espesor.
  - Acción: Se rechaza inmediatamente el pedido con HTTP 422 indicando "No hay stock registrado para este tipo de vidrio y espesor."

## 8. Criterios de aceptación
- **CA-01 (T01):** El repositorio filtra correctamente el stock usando el tipo de vidrio y espesor sin alterar la base de datos.
- **CA-02 (T02):** El validador procesa las dimensiones de las piezas y aprueba el encaje en planchas permitiendo rotación ortogonal.
- **CA-03 (T03):** El validador incluye los retazos reutilizables disponibles como fuentes válidas de material.
- **CA-04 (T04):** Un intento de registrar un pedido con una pieza más grande que cualquier stock disponible retorna HTTP 422 y un mensaje claro.

## 9. Impacto técnico
- **Módulos:**
  - `Inventory`: Modificación de `application/ports.py` y `infrastructure/repositories.py`.
  - `Orders`: Creación de validador en `domain/validators.py` y ajuste en los casos de uso (`application/use_cases.py`).
- **API:** Posibles nuevos códigos de respuesta 422 en el endpoint `POST /api/orders`.
- **BD / migración:** No requiere cambios estructurales; usa tablas existentes (`PLANCHA`, `RETAZO`).

## 10. Pruebas previstas
- **Unitarias (Dominio):** Validación de la lógica geométrica (`fits_geometrically`, `has_candidate`) con mocks de inventario.
- **Integración (Repositorio):** Pruebas de consultas a PostgreSQL para asegurar el correcto filtrado (RN-01, RN-02).
- **API (Caja Negra):** Envío de un pedido válido (retorna 200/201) y envío de un pedido con pieza gigante (retorna 422).

## 11. Evidencias requeridas
- Reporte de pytest demostrando la ejecución exitosa de las pruebas unitarias y de integración.
- Respuestas HTTP capturadas comprobando el error 422 para piezas sin stock.
- Pull Request fusionado aplicando la arquitectura limpia.

## 12. Decisiones / notas
- La responsabilidad técnica se divide: T01 y T02 (infraestructura y dominio geométrico para planchas) por Luis Ibañez, y T03 y T04 (consulta de retazos e integración al caso de uso) por Andro Quispe.