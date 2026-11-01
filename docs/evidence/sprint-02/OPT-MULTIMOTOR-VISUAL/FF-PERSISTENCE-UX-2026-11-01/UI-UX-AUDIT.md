# Auditoría UI/UX transversal y backlog propuesto

Referencia de código/entorno: [informe técnico](README.md). Evaluación local del
01/11/2026; Chromium real, React/Vite, FastAPI y PostgreSQL temporal. Los datos
de las capturas son sintéticos. Se revisaron login/sesiones, Dashboard para los
tres roles y un rol sin funciones, usuarios/permisos, planchas/retazos, pedidos
y comparación/confirmación. No se implementó un rediseño transversal.

## Línea base y método

Fuentes locales leídas:

- `Downloads/Documento_Diseno_UI_UX_Accesibilidad_NewGlass_v1_0.docx`, secciones
  3–14: tokens, jerarquía, estados, formularios, responsive, teclado y evidencias.
- `Downloads/Documento_Estandares_Ingenieria_Desarrollo_NewGlass_v1_0.docx`,
  secciones 6, 9, 12, 15–19: trazabilidad, contratos, pruebas y evidencia.
- `CONTRIBUTING.md`, `docs/ui-ux/feedback-compartido.md`,
  `docs/ui-ux/inventario-base-visual.md` y SPEC vigentes HU-001, HU-003 T04/T05,
  S1-RBAC, HU-004/005, HU-006/007/013/014/016, EN-006, S1-OPT-UI y
  OPT-MULTIMOTOR-VISUAL. Se distinguieron decisiones históricas de la
  implementación posterior: por ejemplo, la antigua sidebar informativa ya
  tiene navegación real. HU-013 aún figura como Draft; no se cambió su estado.

Los dos DOCX se presentan como **propuestas para revisión/aprobación**. Se usan
como línea base solicitada por el usuario, sin atribuirles una aprobación humana
no documentada. El feedback compartido sí tiene su decisión de equipo registrada.

Procedimiento: revisión de código/contratos, recorrido con API real, capturas,
inspección de DOM/estilos calculados, Enter en login, navegación de pestañas con
flechas/Home/End, apertura/cierre de formularios y diálogos, recuperación y
confirmación real. Escritorio 1440×900 y móvil 390×844, más medición de documento
a 320 CSS px en cada estado. Las tablas tienen su propio scroll; no se confundió
ese scroll con desbordamiento horizontal de toda la página.

Los JSON [desktop](ui-observations-desktop.json) y
[mobile](ui-observations-mobile.json) conservan controles, labels, fuentes,
dimensiones, foco, contraste candidato, respuestas HTTP y reflow por estado.
El script [ui-audit.spec.js](ui-audit.spec.js) permite repetir el recorrido.
El término «candidato» identifica mediciones que se contrastaron con el elemento
y su CSS; no equivale a una certificación automatizada.

## Matriz de hallazgos priorizados

Severidad: crítica = resultado operativo perdido; alta = flujo bloqueado,
pérdida de trabajo o barrera de accesibilidad; media = fricción/consistencia;
baja = claridad o mantenimiento. «Abierto» significa propuesta para otro PBI.

| ID | Módulo / severidad / estado | Evidencia y criterio | Solución propuesta |
|---|---|---|---|
| F-01 | Optimización · crítica · **corregido** | FF calculado sin resultado persistido al agotarse la conexión. Incumple integridad/feedback y RN de resultados independientes. Prueba PostgreSQL real con `TimeoutError`. | Liberar lectura RBAC antes del UoW, pool acotado y correlación del error. Ver informe técnico. |
| F-02 | Optimización · alta · **corregido** | BF confirmado conservaba pestañas, selección y recuperación automática. Capturas antes/después; línea base §§3, 8, 9 y flujo solicitado. | Transición explícita a pendientes, generación de solicitudes, almacenamiento limpio y foco. Historial consultable por ID. |
| F-03 | Compartido / Dashboard · alta · **corregido** | Autorización retenida más sesión propia de Inventario: saturación de pool durante consultas del Dashboard. Caso real descubierto al ampliar la regresión. | Finalizar lectura en `require_permission`, sin cambiar permisos; prueba con 8 lectores y pools 1/5. |
| A-01 | Optimización · alta · **abierto** | Foco de pestañas: `rgb(67,187,174)` / `#43bbae`, outline 3 px. Contraste ≈2,34:1 contra blanco y ≈2,09:1 contra `#edf3f1`. Medición `14b`, foco real con teclado. No llega a 3:1 requerido por 1.4.11. | Reutilizar token `--ng-primary-focus`, comprobar contraste contra ambos fondos y conservar foco no oculto. |
| A-02 | Optimización · alta · **abierto** | Texto `#647a79`: «Comparación finalizada» sobre `#f4f9f7` ≈4,29:1; ayuda de elección sobre `#f5faf7` ≈4,32:1; unidades sobre `#fbfdfc` ≈4,47:1. Texto normal activo: umbral 4,5:1 (1.4.3). Estados `14b/14c`. | Unificar tokens y oscurecer texto secundario en superficies tintadas; validar pares exactos sin redondear umbrales. |
| N-01 | Compartido / navegación · media · **abierto** | Tras cambiar módulo, el foco queda en BODY en estados 04, 07, 11 y 14. El botón del módulo anterior se desmonta. Hay enlace «Saltar al contenido», pero no anuncio del nuevo contexto. Línea base §§8, 10. | Llevar foco al título principal al navegar, con anuncio moderado; prueba teclado y lector de pantalla. No se declara fallo WCAG solo por observar BODY. |
| N-02 | Usuarios · media · **abierto** | Alta enfoca H2 correctamente; al cancelar no hay restitución al disparador. `UserForm` solo tiene efecto de entrada, `UsersPage` no guarda trigger. La SPEC HU-003 T04/T05 ya registra esta mejora pendiente. | Guardar botón de origen y devolverle foco al cerrar/guardar. |
| N-03 | Inventario · media · **abierto** | Registrar plancha/retazo sustituye listado por formulario y deja foco en BODY (08/10); contraste con alta de usuario que sí enfoca título. | Patrón compartido de entrada/salida de formularios con foco y retorno consistente. |
| D-01 | Pedidos · alta · **abierto** | `GestionPedidos.closeOrderModal` y Escape cierran sin consultar cambios; el botón Cancelar interno sí pide confirmación. Permite perder edición no guardada por X/Escape. Revisión de handlers y caracterización en recorrido. BD no se altera. Línea base §6.1, prevención de errores. | Una única política dirty para Cancelar/X/Escape; confirmar descarte y conservar formulario si se cancela. |
| V-01 | Optimización · media · **abierto** | `ComparisonWorkspace.css` introduce paleta verde, radios 14/16 y espaciados .7/.8/1.3 rem frente a tokens azules 8/12 y escala 4/8. Capturas 14 y después. Línea base §§5–6. | PBI de normalización gradual de tokens, sin tocar geometría ni ejecución. |
| V-02 | Optimización · media · **abierto** | H2 «Comparar distribuciones» llega a 2,2 rem, compite con H1 de 32 px y repite instrucciones. En móvil, fases usan .68 rem (10,88 px), bajo preferencia 12–14 px. | Simplificar jerarquía; una cabecera principal y fases legibles. Esto es desviación de diseño, no fallo WCAG por tamaño de texto aislado. |
| V-03 | Inventario · media · **abierto** | En escritorio 1440, tabla de planchas mide 1151 px en contenedor de 972 px: acciones quedan fuera de vista. Estado 07. El scroll es operable con teclado y está rotulado. | Indicar desplazamiento también en escritorio; evaluar acciones fijas/contextuales y prioridades de columnas. No es por sí solo incumplimiento 1.4.10: tablas tienen excepción. |
| V-04 | Dashboard / compartido · media · **abierto** | En móvil, menú abierto y sesión ocupan aproximadamente la primera mitad de 844 px; los accesos rápidos del Dashboard van después de resúmenes/listado. Capturas 03 y 16. | Prototipo de navegación móvil compacta y priorización de acciones. Conservar todas las funciones y permisos. |
| V-05 | Usuarios/permisos · baja · **abierto** | Códigos como `inventory.view` visibles bajo cada descripción. Útiles para administración técnica, añaden densidad para gestión habitual; no son el nombre principal del control. Estado 06. | Evaluar detalle técnico desplegable y agrupación por tarea, sin ocultar implicaciones del permiso. |
| V-06 | Inventario · baja · **abierto** | Botones de fila «Editar» repiten nombre; Historial y Baja sí incluyen identificador accesible. El contexto de fila existe mediante encabezados de tabla. | Añadir nombre contextual a Editar y conservar texto visible breve. Mejora, no fallo automático de nombre accesible. |
| V-07 | Optimización · baja · **abierto** | «1 unidades» en solicitud y decimales sin formato uniforme (por ejemplo seis ceros en mm²). La magnitud y unidad son reales. Estado 14b y capturas de comparación. | Plurales y formateador por magnitud, manteniendo precisión del contrato y datos originales. |
| N-04 | Navegación · baja · **propuesta** | La vista activa está en estado React y todas las pantallas conservan pathname `/`; refresh vuelve a Inicio. Es compatible con CA-18 de Dashboard. | Evaluar URLs recuperables y Back/Forward en un PBI futuro. No modificar routing dentro de esta corrección. |
| E-01 | Documentación · baja · **abierto** | Algunas SPEC describen bases históricas (sidebar informativa, consumo «futuro») mientras documentos posteriores las amplían; HU-013 continúa Draft. | Reconciliar trazabilidad/estados con reviewers; conservar historia y enlazar ampliaciones, sin simular aprobación. |

## Comprobaciones positivas y cobertura por módulo

| Módulo | Comprobado | Límite de la evidencia |
|---|---|---|
| Login y sesión | Labels visibles/asociados; error de campos vacíos mediante Enter, `aria-invalid` y descripción; contraseña con toggle nombrado; autocomplete; loading; logout. Pruebas backend/componentes cubren 401/403/expiración/conexión. | El recorrido no equivale a prueba con NVDA/VoiceOver ni de todas las tecnologías de asistencia. El error inicial mantiene foco en Ingresar: valorar foco al primer inválido. |
| Dashboard por roles | Administrador, Operario, Almacenero y rol sin funciones; opciones según permisos, estado vacío, actualización y cierre de sesión. Cifras desde respuestas reales; la suite verifica seis fuentes (dos para Almacenero). | Los textos informativos son extensos; priorización requiere validación con usuarios reales. |
| Usuarios y permisos | Listado primero, alta bajo acción, filtros con labels, encabezados de tabla, rol/estado, sin columna separada de DNI; tabs con teclado; controles etiquetados; guardas backend. | No se guardaron permisos ni se crearon/desactivaron cuentas reales. Mutaciones y errores están en suites de componentes/API aisladas. |
| Inventario | Planchas y retazos, unidades mm, filtros, alta/retorno; tabla con scroll rotulado y foco. Código usa diálogo para bajas y muestra historial. Fixtures y pruebas comprueban trazabilidad. | No se realizaron bajas en una base compartida. Las acciones extensas necesitan la mejora V-03. |
| Pedidos | Listado/filtros/paginación; nuevo y edición de pedido real; modal nombrado, cierre Escape, foco inicial en cerrar y retorno al disparador. Cantidad de la pieza coincide con API. | Política dirty inconsistente D-01. Los estados no editables y validación geométrica están cubiertos por componentes/API; no se rediseñaron. |
| Optimización | Cuatro pestañas, semántica tablist/tabpanel, flechas/Home/End, fases, solicitud original, IDs por motor, valores del backend, selección explícita; stock intacto al simular; confirmación y liberación diferenciadas; errores/recovery; reducción de movimiento; desktop/móvil. | Permanecen A-01/A-02 y normalización visual. No existe animación histórica durable después de reiniciar; se informa 410 y se conservan resultados. |

Los controles frecuentes observados usan generalmente 44 px y radios de 8 px.
No se clasificaron como infracción de tamaño los checkbox de 13/20 px por su
rectángulo aislado: tienen labels clicables mayores y debe evaluarse el objetivo
completo y el espaciado. Los controles deshabilitados no se trataron como texto
activo para contraste. La medición de contraste excluye fondos con imagen,
transparencias y estados que requieren una comprobación adicional.

No se observó overflow horizontal del documento en los estados medidos, tampoco
a 320 CSS px. La tabla comparativa sí conserva scroll interno (1059 px en región
de 260 px a 320). No se afirma que medir 390 px certifique 400% de zoom. La
evaluación tampoco certifica WCAG 2.2 AA ni ISO 9241-210. Lighthouse no se ejecutó:
el proyecto no tiene ese arnés instalado; no se asigna un puntaje ficticio.

## PBIs propuestos, sin crear tareas externas

| Prioridad | Propuesta | Criterio de aceptación mínimo |
|---|---|---|
| P1 | Accesibilidad de comparación (A-01/A-02) | Todos los pares de texto activo alcanzan 4,5:1 y foco 3:1 sobre fondos adyacentes; teclado y reducción de movimiento conservados; capturas y medición reproducible. |
| P1 | Protección de borradores de pedido (D-01) | Cancelar/X/Escape comparten política dirty; nunca se pierde edición sin decisión explícita; cancelar descarte conserva campos y foco. |
| P2 | Foco y navegación compartidos (N-01/02/03) | Entrar a un módulo/formulario anuncia título; cerrar devuelve foco al disparador; recorrido completo con teclado y NVDA. |
| P2 | Normalizar tokens/jerarquía del comparador (V-01/02) | Reutilizar paleta, radios y escala aprobados; fases legibles a 320/390; métricas/algoritmos/contratos sin cambios. |
| P2 | Tablas operativas de inventario (V-03/06) | Acciones identificables y localizables a 1366 px; scroll accesible; nombres contextuales y unidades reales. |
| P2 | Navegación y acciones en móvil/Dashboard (V-04) | Prototipo evaluado por roles; acceso a tarea principal sin recorrer todo el resumen; sin pérdida de funciones a 320 px. |
| P3 | Claridad de permisos/métricas (V-05/07) | Lenguaje funcional principal, detalle técnico opcional, plurales correctos, unidades y precisión coherentes. |
| P3 | Evidencia accesible continua | Lighthouse por pantalla como complemento, revisión manual con lector de pantalla, zoom, errores/loading y navegadores adicionales; ningún puntaje se presenta como certificación. |
| P3 | Reconciliar navegación y documentación (N-04/E-01) | Decisión de URLs explícita; SPEC históricas enlazan ampliaciones y el reviewer valida estados. |

## Referencias técnicas de accesibilidad

Se consultaron las fuentes primarias W3C el 01/11/2026:

- [Contraste de texto, SC 1.4.3](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html): umbrales y excepciones de texto inactivo/grande.
- [Contraste no textual, SC 1.4.11](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html): indicadores de foco y estados contra colores adyacentes.
- [Foco visible, SC 2.4.7](https://www.w3.org/WAI/WCAG22/Understanding/focus-visible.html): operación perceptible mediante teclado.
- [Reflow, SC 1.4.10](https://www.w3.org/WAI/WCAG22/Understanding/reflow.html): referencia de 320 CSS px y excepción de tablas/diagramas.
- [Tamaño de objetivo, SC 2.5.8](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html): objetivo/espaciado y excepciones; no basta medir la caja del input.

Los ratios publicados se redondean solo para lectura; la clasificación usa el
umbral aplicable sin redondearlo a favor del resultado.
