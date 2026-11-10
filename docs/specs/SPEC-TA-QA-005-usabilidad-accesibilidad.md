# SPEC-TA-QA-005 — Usabilidad y Accesibilidad

## Información general

| Campo | Valor |
|---|---|
| ID | TA-QA-005 |
| Tarea | Usabilidad y Accesibilidad en Módulos Clave de NewGlass |
| Sprint | Sprint 2 |
| Prioridad / Tipo | Alta / QA & UX-A11y |
| Estado | Verified (Completado y Verificado contra Supabase) |
| Responsable | Luis Anthony Ibañez Herrera |
| Reviewer | Fabricio Melendez Quezada |
| Rama | `qa/TA-QA-005-usabilidad-accesibilidad` |
| Base | `integration-02` en commit `b964b2b` |
| Fecha de inicio | 09/11/2026 |
| Dependencias | Backend real (`backend/main.py`), PostgreSQL real (Supabase), Frontend Vite/React (`frontend/src/`) |
| Evidencia | [`docs/evidence/sprint-02/TA-QA-005/README.md`](../evidence/sprint-02/TA-QA-005/README.md) y [`Notion/TA-QA-005/Evidencia_Notion_TA-QA-005.docx`](../../../../Notion/TA-QA-005/Evidencia_Notion_TA-QA-005.docx) |

---

## 1. Objetivo

Evaluar de manera empírica, cuantitativa y con conexiones reales la **usabilidad y accesibilidad (UX / A11y)** del sistema NewGlass en sus tres módulos operacionales centrales: **Pedidos**, **Inventario** y **Optimización**:

1. Definir escenarios de uso y tareas concretas que un usuario debe completar en cada módulo.
2. Medir tiempos de interacción de tareas, tasa de errores de usuario y porcentaje de completitud (*Task Completion Rate*).
3. Evaluar el cumplimiento de accesibilidad universal bajo lineamientos **WCAG 2.1 nivel AA**:
   - Operabilidad 100% por teclado (`Tab`, `Shift+Tab`, `Enter`, `Space`, `Escape`) sin requerir mouse.
   - Manejo y trampa de foco (*focus trap* y restauración de foco al cerrar modales).
   - Semántica de atributos ARIA y etiquetas descriptivas.
4. Auditar el comportamiento responsivo en dispositivos móviles ($\le 375\text{ px}$ y $390\text{ px}$) verificando ausencia de desbordamiento horizontal (`scrollWidth <= innerWidth`) y tamaños de objetivos táctiles (*touch targets* $\ge 44 \times 44\text{ px}$).
5. Documentar exhaustivamente las fricciones y barreras detectadas, estructurando una **Matriz de Problemas Encontrados y Propuestas de Mejora**.

---

## 2. Alcance

### Incluye
* **Módulo de Pedidos:** Flujo de creación de pedido con piezas rectangulares y poligonales convexas, selector accesible de clientes, edición interactiva y guardado.
* **Módulo de Inventario:** Consulta y filtrado de stock de planchas y retazos, diálogo modal de registro de planchas y diálogo de baja/merma con motivo.
* **Módulo de Optimización:** Selección de orden, espacio de trabajo multi-motor, tabla de medidas originales, visualización 2D/3D y confirmación.
* **Pruebas con Conexiones Reales:** Pruebas contra la API real de FastAPI y la base de datos PostgreSQL real (Supabase), sin mocks ni datos simulados que oculten fallas de integración.
* **Métricas cuantitativas:** Tiempo de tarea ($T$), porcentaje de tareas exitosas ($C\%$), y frecuencia de errores de navegación/validación ($E$).
* **Auditoría de Accesibilidad:** Manejo de foco, contraste, atributos ARIA, navegación por teclado y responsividad móvil.
* **Matriz de Mejoras:** Propuestas de solución de ingeniería y diseño para cada problema detectado.

### Fuera de alcance
* Rediseño completo de la arquitectura visual de la aplicación.
* Pruebas de compatibilidad con lectores de pantalla propietarios externos de pago (JAWS); se evalúa semántica ARIA estandarizada.

---

## 3. Actor y Precondiciones

* **Actores:**
  - Operario de Producción (`id_rol = 1`) y Administrador (`id_rol = 3`).
* **Precondiciones:**
  1. Servidor backend real de FastAPI activo en `http://127.0.0.1:8000` con conexión a la base de datos PostgreSQL real de Supabase (`aws-0-us-east-1.pooler.supabase.com`).
  2. Servidor frontend Vite activo en `http://127.0.0.1:5173`.
  3. Base de datos con catálogo real de tipos de vidrio, espesores, clientes y usuarios.

---

## 4. Escenarios de Uso y Tareas Concretas

| Módulo | ID Tarea | Nombre de la Tarea | Descripción / Flujo Concreto | Criterio de Éxito |
|---|---|---|---|---|
| **Pedidos** | **T-PED-01** | Búsqueda y Selección de Cliente | Abrir diálogo de nuevo pedido, buscar cliente por nombre o documento y seleccionarlo. | Cliente asignado, foco transferido al formulario de piezas. |
| **Pedidos** | **T-PED-02** | Configuración de Pieza Poligonal | Ingresar lados, milímetros de segmentos, validar convexidad en tiempo real y agregar al pedido. | Pieza validada y agregada al resumen sin desbordamiento. |
| **Pedidos** | **T-PED-03** | Registro Completo solo con Teclado | Completar todo el flujo de nuevo pedido usando exclusivamente teclas `Tab`, `Enter`, flechas y `Escape`. | Pedido persistido en base de datos (HTTP 201) sin intervención de ratón. |
| **Inventario**| **T-INV-01** | Filtrado de Stock de Planchas | Filtrar planchas por tipo de material y espesor de 6 mm desde la interfaz de inventario. | Tabla de stock actualizada reflejando únicamente el material filtrado. |
| **Inventario**| **T-INV-02** | Registro de Plancha con Teclado | Abrir diálogo "Registrar plancha", ingresar medidas y cantidad mediante teclado y guardar. | Diálogo cerrado, nueva plancha persistida, foco devuelto al botón de apertura. |
| **Inventario**| **T-INV-03** | Baja de Retazo y Manejo de Foco | Abrir diálogo de baja de retazo, seleccionar motivo, confirmar y validar trampa de foco. | Foco contenido dentro del modal; al cerrar, foco en el elemento de origen. |
| **Optimización**| **T-OPT-01** | Navegación e Inspección 2D/3D | Cargar orden de optimización, conmutar entre vistas 2D y 3D, e inspeccionar tabla de medidas. | Renderizado fluido sin scroll horizontal en viewport móvil ($375\text{ px}$). |
| **Optimización**| **T-OPT-02** | Selección de Motor y Confirmación | Seleccionar método de optimización recomendado y proceder con la confirmación de corte. | Flujo de confirmación completado y trazabilidad de materiales visible. |

---

## 5. Reglas de Negocio y Técnicas (RN)

* **RN-01 (Conexión Real Obligatoria):** Todas las pruebas de usabilidad e integración deben comunicarse con el servidor backend real (`main.py`) y la base de datos PostgreSQL real. Queda estrictamente prohibido el uso de mocks o respuestas sintéticas simuladas en estas verificaciones.
* **RN-02 (Accesibilidad 100% por Teclado - WCAG 2.1.1):** Todos los botones, campos de entrada, selectores y modales deben ser alcanzables y operables exclusivamente con el teclado (`Tab`, `Shift+Tab`, `Enter`, `Space`, `Escape`). Ningún elemento interactivo puede carecer de indicador visual de foco (`:focus-visible`).
* **RN-03 (Trampa y Gestión de Foco - WCAG 2.4.3):** Al abrir un diálogo modal (`role="dialog"`), el foco debe atraparse dentro del modal (no puede saltar a elementos del fondo). Al pulsar `Escape` o cerrar el diálogo, el foco debe regresar exactamente al botón que lo activó.
* **RN-04 (Adaptabilidad Móvil - WCAG 1.4.10):** En resoluciones móviles estándar ($375 \times 667\text{ px}$ y $390 \times 844\text{ px}$), la aplicación no debe presentar desbordamiento horizontal involuntario (`document.documentElement.scrollWidth <= window.innerWidth`).
* **RN-05 (Áreas de Toque Táctil - WCAG 2.5.5):** Los objetivos interactivos en dispositivos móviles deben contar con una superficie de contacto de al menos $44 \times 44\text{ px}$ para evitar pulsaciones erróneas.
* **RN-06 (Métricas Cuantitativas de Usabilidad):** Se deben medir y tabular:
  - Tiempo medio de completitud por tarea en segundos ($T$).
  - Tasa de finalización exitosa ($C\% = \frac{\text{Tareas exitosas}}{\text{Tareas totales}} \times 100$).
  - Tasa de errores cometidos ($E$).

---

## 6. Criterios de Aceptación (CA)

* **CA-01 (Ejecución sobre Entorno Real):** Todas las pruebas se ejecutan contra el backend FastAPI real y la base de datos PostgreSQL real (Supabase), sin mocks ni simulaciones.
* **CA-02 (Cobertura de Escenarios Pedidos, Inventario y Optimización):** Se evalúan y registran las 8 tareas concretas definidas para los tres módulos.
* **CA-03 (Métricas Cuantitativas de Usabilidad):** Se reportan formalmente los tiempos de completitud, tasa de errores y porcentaje de éxito por tarea.
* **CA-04 (Operabilidad por Teclado y Foco):** Se comprueba la navegación sin mouse y la contención de foco en modales de pedidos, inventario y optimización.
* **CA-05 (Responsividad Móvil Verificada):** Se comprueba la ausencia de scroll horizontal y la legibilidad en pantallas móviles de $375\text{ px}$.
* **CA-06 (Matriz de Problemas y Mejoras):** Se entrega una matriz detallada con los hallazgos de usabilidad detectados, su nivel de severidad y las propuestas de mejora recomendadas.

---

## Historial de Estado

* **2026-11-09:** *Draft* — Creado bajo metodología SDD con mandato de conexiones reales.
* **2026-11-09:** *In-Progress* — Aprobado para diseño y ejecución de pruebas.
