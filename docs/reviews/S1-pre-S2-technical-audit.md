# Auditoría técnica de Sprint 1 — NewGlass

**Fecha:** 18/10/2026, America/Lima.  
**Rama verificada:** `integration/sprint-01`.  
**HEAD verificado:** `9546993e6a3dc39507b37179c3734bdf45208131`.  
**Estado del repositorio al cierre de la auditoría, antes de crear este documento:** limpio, sin cambios.  
**Alcance:** auditoría del repositorio real. Este informe no aplica las correcciones propuestas.

Las rutas y líneas citadas corresponden al HEAD auditado. Los resultados de pruebas documentados pertenecen a la auditoría previa; la creación autorizada de este documento no implica una nueva ejecución de pruebas.

## 1. Resumen ejecutivo

**Recomendación: resolver los dos BLOCKER antes de iniciar Sprint 2 y abordar los HIGH al inicio del sprint.** El diseño base es adecuado: FastAPI como monolito modular, separación de capas, dominio independiente de frameworks y frontend sin acceso directo a PostgreSQL. No hay evidencia que justifique cambiar de framework, base de datos o arquitectura de despliegue.

La confirmación es uno de los puntos más sólidos: bloquea y revalida los recursos relevantes y aplica los cambios mediante una transacción. La simulación no consume stock. Sin embargo, existen problemas alrededor del ciclo de vida de las ejecuciones, la disponibilidad efectiva del inventario y los límites operacionales.

Los principales resultados son:

- La previsualización histórica puede dejar pedidos en un estado incompatible con la ejecución First Fit.
- Los límites de rasterización por objeto no limitan la cantidad total de piezas, unidades de stock, trabajo acumulado o ejecuciones concurrentes.
- Falta un flujo completo de recuperación de ejecuciones fallidas y resultados cuyo stock ya no está disponible.
- Es posible volver a marcar como disponible un retazo consumido y editar cantidades de planchas sin generar movimientos de inventario.
- El seed de permisos puede restaurar permisos retirados deliberadamente de un rol.
- Algunas pruebas E2E pueden omitirse en CI por configuración y dejar el pipeline verde sin ejecutar la cobertura prevista.
- La futura promoción a `main` requiere tratar explícitamente el merge del PR #52 y su reversión mediante el PR #53; un merge ordinario no garantiza restaurar el contenido revertido.

### Evidencia de validación

Se inspeccionaron implementaciones, contratos, modelos, migraciones, pruebas, configuración y documentación antes de seleccionar las pruebas útiles. No se ejecutó inicialmente toda la suite.

| Validación seleccionada | Resultado | Alcance |
| --- | ---: | --- |
| Backend | 857 pruebas aprobadas | Dominio, rasterización, inventario, autenticación, usuarios, integración y casos de concurrencia/rollback seleccionados |
| Frontend unitario | 68 pruebas aprobadas | Contratos, estados, geometría, escena y configuración de staging |
| Frontend de componentes | 88 pruebas aprobadas | Pedidos, selección, editor, 3D, contratos, Dashboard y confirmaciones |
| Total | **1.013 pruebas aprobadas** | Selección orientada a los hallazgos, no certificación de toda la suite |

También se realizaron reproducciones sintéticas dirigidas, inspección estática de dependencias entre capas y comprobación de `git diff --check`. No se encontraron ciclos de importación internos en el alcance inspeccionado ni cambios pendientes al finalizar la auditoría.

Las pruebas de integración utilizadas se ejecutaron con PostgreSQL temporal en loopback. No se ejecutaron migraciones sobre bases compartidas ni se utilizó la base configurada en el `.env` del proyecto para estas validaciones.

### Límites de la conclusión

No se ejecutó la suite completa ni la batería E2E completa. Tampoco se verificaron remotamente las protecciones de ramas, las Config Vars reales de Heroku, los grants/RLS actuales de Supabase o el estado del despliegue publicado. La revisión de UX se apoyó en código, CSS y pruebas de componentes; no constituye una certificación visual y de accesibilidad mediante navegación real en todos los tamaños de pantalla.

Se distingue entre **defecto confirmado**, **riesgo**, **deuda técnica**, **mejora** y **preferencia estilística**. Las pruebas aprobadas no se utilizan como sustituto de revisar la implementación.

## 2. Estado por módulo

| Módulo o área | Estado | Evaluación |
| --- | --- | --- |
| Arquitectura | Adecuada, con deuda localizada | Se conserva el monolito modular y la separación de capas; conviene reducir duplicación y concentración de responsabilidades donde ya producen riesgos concretos. |
| Autenticación | Funcional; requiere endurecimiento | Los permisos actuales se consultan en BD. Faltan decisiones y controles sobre intentos, revocación de sesiones y validación de configuración. |
| Usuarios y RBAC | Requiere correcciones | El seed no preserva un rol deliberadamente vacío y la protección del último administrador es insuficiente con permisos delegados. |
| Clientes | Adecuado para Sprint 1 | Listados sin paginación y ambigüedad de reintentos deben abordarse según volumen y flujos de creación. |
| Inventario | Requiere correcciones prioritarias | La confirmación es sólida, pero la edición manual puede romper la trazabilidad y la disponibilidad declarada de retazos consumidos. |
| Pedidos | Funcional, con problemas de integración y UX | La edición geométrica y el agrupamiento están implementados; deben corregirse permisos visibles, cierre de formularios y transición hacia optimización. |
| Optimización | Motor sólido; ciclo de vida incompleto | El resultado persistido y sus métricas son coherentes; faltan límites globales y recuperación operacional. |
| Rasterización | Adecuada por objeto | Las protecciones existentes no acotan por sí solas el costo total de una solicitud o de varias ejecuciones concurrentes. |
| Confirmación | Sólida | Revalidación, bloqueos y rollback protegen frente a mutaciones parciales y doble consumo. |
| Dashboard | Adecuado para poco volumen | Obtiene datos completos para calcular indicadores; conviene medir payload y consultas antes de ampliar el volumen. |
| Base de datos | Consistente en lo esencial | Hay integridad y trazabilidad estructural; aparecen desajustes numéricos y consultas que requieren medición. |
| CI/CD y repositorio | Requiere ajustes | Existen gates y documentación, pero hay skips E2E posibles, referencias obsoletas y una promoción a `main` que necesita procedimiento explícito. |

## 3. Fortalezas

1. **La arquitectura sigue siendo un monolito modular.** La inspección de importaciones no encontró dependencias de FastAPI, SQLAlchemy, Supabase o HTTP en Domain ni violaciones internas relevantes de las capas revisadas.
2. **El frontend no accede directamente a PostgreSQL.** No se encontró un cliente de BD ni una cadena de conexión productiva utilizada por React.
3. **La autorización consulta el estado actual en BD.** No depende exclusivamente de permisos congelados en el JWT.
4. **Simular no modifica stock.** Sí puede persistir ejecuciones y estados del flujo; eso debe distinguirse de consumir inventario.
5. **La confirmación es transaccional.** Las pruebas con PostgreSQL real cubren bloqueos, concurrencia y rollback, además de las comprobaciones en código.
6. **Una segunda confirmación no vuelve a consumir stock.** Devuelve conflicto. Es idempotente respecto del efecto sobre inventario, aunque no devuelve necesariamente el mismo comprobante de la primera respuesta.
7. **El consumo se calcula por unidades físicas de material utilizado**, no por número de piezas colocadas.
8. **El resultado se conserva en un snapshot versionado.** Confirmar no ejecuta de nuevo First Fit para reconstruir una solución potencialmente distinta.
9. **El editor distingue geometría provisional de geometría guardable**, incluyendo `preview_vertices_mm` y validación progresiva.
10. **La estrategia de pruebas incluye integración real con PostgreSQL.** Los comportamientos críticos no descansan exclusivamente en mocks o SQLite.

## 4. Hallazgos backend

### S1-04 — Retazos consumidos pueden volver a declararse disponibles

- **Severidad:** HIGH.
- **Clasificación:** defecto confirmado.
- **Área:** inventario, selección de material y trazabilidad.
- **Archivos:** `backend/app/modules/inventory/application/service.py:164`; `backend/app/modules/optimization/infrastructure/stock_adapter.py`; `backend/app/modules/optimization/infrastructure/confirmation_adapter.py`.
- **Evidencia:** `update_retazo` no aplica una protección equivalente a la de consumo de la confirmación. Se reprodujo la secuencia confirmar consumo → `PATCH` de disponibilidad a verdadero → retazo activo. También fue posible efectuar una baja manual posterior, dejando en el historial `CONSUMO_OPTIMIZACION` y `BAJA_ROTURA`. La selección de candidatos considera el estado disponible. La confirmación sí rechaza un segundo consumo del mismo retazo.
- **Riesgo:** ofrecer material físicamente consumido, producir simulaciones imposibles de confirmar y mantener un historial contradictorio. No se afirma que la segunda confirmación consiga consumirlo: esa protección existe.
- **Solución recomendada:** compartir la regla de elegibilidad para operaciones sobre retazos; impedir reactivación y baja de retazos ya consumidos, preservando el tratamiento explícito de datos históricos.
- **Esfuerzo aproximado:** 1–2 días.
- **SPEC / ADR / migración:** SPEC sí; ADR no; migración no necesariamente.
- **Pruebas necesarias:** consumir, editar, intentar reactivar, intentar dar de baja y volver a seleccionar candidatos; comprobar que el origen y el historial permanecen coherentes.

### S1-05 — Edición de cantidades sin movimiento de inventario

- **Severidad:** HIGH.
- **Clasificación:** deuda técnica con comportamiento confirmado.
- **Área:** inventario y auditoría de stock.
- **Archivos:** `backend/app/modules/inventory/application/service.py:115`; `backend/app/modules/inventory/infrastructure/repository.py:303`; `frontend/src/features/inventory/InventoryPage.jsx:394`.
- **Evidencia:** editar la cantidad de una plancha permite establecer, por ejemplo, `cantidad=0` sin generar un movimiento nuevo. El formulario de inventario expone esta edición.
- **Riesgo:** el saldo deja de poder explicarse a partir de movimientos. La confirmación puede ser correcta y aun así coexistir con ajustes manuales que eliminan trazabilidad.
- **Solución recomendada:** separar edición de metadatos y ajuste de existencias. Registrar saldo anterior, variación, motivo y actor en una operación atómica. No se recomienda prohibir operaciones manuales legítimas de inventario.
- **Esfuerzo aproximado:** 2–3 días.
- **SPEC / ADR / migración:** SPEC sí; ADR no; migración probablemente necesaria si se introduce un tipo de movimiento o datos de ajuste nuevos.
- **Pruebas necesarias:** ajustes positivos y negativos, concurrencia con confirmación, rollback y reconciliación entre saldo y movimientos.

### S1-06 — El seed restaura permisos retirados de un rol

- **Severidad:** HIGH.
- **Clasificación:** defecto confirmado.
- **Área:** RBAC y bootstrap.
- **Archivo:** `backend/app/modules/authentication/infrastructure/permission_seed.py:35`.
- **Evidencia:** el seed interpreta un rol sin permisos como un rol pendiente de inicialización. Se reprodujo un rol Operario deliberadamente vacío que pasó de 0 a 8 permisos al ejecutar el seed. El dominio permite un conjunto vacío; la cobertura existente que elimina un permiso no detecta este caso.
- **Riesgo:** un reinicio o bootstrap puede restablecer autorizaciones retiradas por un administrador.
- **Solución recomendada:** distinguir creación inicial de un rol y mantenimiento del catálogo de permisos. No inferir que un rol está sin inicializar porque no tenga permisos.
- **Esfuerzo aproximado:** 0,5–1 día.
- **SPEC / ADR / migración:** SPEC sí; ADR no; migración evitable según la implementación elegida.
- **Pruebas necesarias:** rol nuevo, rol deliberadamente vacío, rol parcialmente configurado, incorporación de un permiso al catálogo y ejecución repetida del seed.

### S1-09 — Reintentos ambiguos en operaciones con efectos

- **Severidad:** HIGH.
- **Clasificación:** riesgo sustentado por la implementación.
- **Área:** bajas de inventario y creación de pedidos.
- **Archivos:** `backend/app/modules/inventory/application/service.py:194`; `backend/app/modules/orders/infrastructure/repositories.py:22`; `frontend/src/features/inventory/InventoryPage.jsx:573`; `frontend/src/features/orders/FormularioPedido.jsx:334`.
- **Evidencia:** repetir una baja parcial crea otra baja si queda stock. Si la transacción se confirma pero la respuesta se pierde, el cliente no dispone de una identidad de operación para distinguir un reintento de una operación nueva. En creación de pedidos se conserva el borrador tras el error, lo que permite reintentar una creación que pudo haberse confirmado.
- **Riesgo:** doble descuento o pedidos duplicados ante pérdida de respuesta. No se encontró evidencia de que ya haya ocurrido en producción.
- **Solución recomendada:** identidad de operación para las mutaciones relevantes, persistencia de su resultado y consulta o repetición segura. No deduplicar por cliente, contenido o medidas: dos operaciones idénticas pueden ser legítimas.
- **Esfuerzo aproximado:** 2–3 días.
- **SPEC / ADR / migración:** SPEC sí; ADR no obligatorio; migración probablemente necesaria.
- **Pruebas necesarias:** respuesta perdida después del commit, solicitudes concurrentes con la misma identidad y reutilización de identidad con un payload diferente.

### S1-12 — Errores de validación pueden devolver contraseñas

- **Severidad:** MEDIUM.
- **Clasificación:** defecto confirmado.
- **Área:** autenticación, usuarios y manejo de errores.
- **Archivos:** `backend/app/modules/authentication/presentation/schemas.py:5`; `backend/app/modules/users/presentation/schemas.py`; `backend/app/main.py`.
- **Evidencia:** una solicitud sintética de login con contraseña inválida por longitud produjo un 422 cuyo `detail[].input` contenía el valor de la contraseña. Los módulos de Pedidos y Clientes sí cuentan con tratamiento para sanear errores de validación.
- **Riesgo:** la contraseña puede quedar expuesta en capturas o registros de respuestas. No es una filtración demostrada hacia otro usuario.
- **Solución recomendada:** sanear los errores de validación para no devolver valores sensibles, manteniendo ubicación, tipo y mensaje útil del error.
- **Esfuerzo aproximado:** 0,5 día.
- **SPEC / ADR / migración:** SPEC no indispensable; ADR no; migración no.
- **Pruebas necesarias:** contraseñas inválidas, campos adicionales, tipos incorrectos y ausencia de secretos en respuestas de error.

### S1-13 — Política incompleta de intentos y revocación de sesiones

- **Severidad:** MEDIUM.
- **Clasificación:** riesgo; no se demuestra incumplimiento de un requisito explícito de Sprint 1.
- **Área:** autenticación, JWT y variables de entorno.
- **Archivos:** `backend/app/modules/authentication/application/use_cases.py:20`; `backend/app/shared/security/tokens.py`; configuración de `backend/app/shared/config`; `backend/app/modules/users/infrastructure/sqlalchemy_user_repository.py:69`.
- **Evidencia:** no se encontró limitación de intentos en la aplicación; el usuario inexistente evita el cálculo bcrypt; cambiar la contraseña no revoca por sí solo los JWT emitidos; la clave se valida como no vacía, sin una política adicional de fortaleza. La duración predeterminada es de ocho horas.
- **Riesgo:** intentos repetidos, diferencias temporales observables y sesiones utilizables después de un cambio de contraseña. Los permisos actuales sí se consultan en BD.
- **Solución recomendada:** definir la política de intentos y revocación, validar la configuración mínima y aplicar controles proporcionales. No introducir Redis por defecto.
- **Esfuerzo aproximado:** 1–3 días, según la política acordada.
- **SPEC / ADR / migración:** SPEC sí; ADR no obligatorio; migración posible si se incorpora una versión de sesión.
- **Pruebas necesarias:** límites de intentos, tratamiento de usuarios inexistentes, cambio de contraseña y uso de un token anterior.

### S1-14 — Protección insuficiente del último administrador

- **Severidad:** HIGH.
- **Clasificación:** defecto confirmado en la lógica de autorización y riesgo de concurrencia.
- **Área:** usuarios y permisos delegados.
- **Archivo:** `backend/app/modules/users/application/use_cases.py:88`.
- **Evidencia:** la protección impide ciertas modificaciones sobre el propio usuario, pero no preserva por sí misma la existencia de una cuenta administrativa activa. Se reprodujo con repositorio en memoria que otro usuario autorizado mediante `users.manage` puede desactivar al último administrador. Tampoco hay una protección transaccional suficiente frente a desactivaciones cruzadas concurrentes.
- **Riesgo:** perder la capacidad de administración y requerir recuperación manual de datos.
- **Solución recomendada:** definir y proteger transaccionalmente la existencia de una cuenta con capacidad administrativa activa, considerando que los permisos son configurables y no solamente nombres de rol.
- **Esfuerzo aproximado:** 1–2 días.
- **SPEC / ADR / migración:** SPEC sí; ADR no; migración no necesariamente.
- **Pruebas necesarias:** último administrador, permisos delegados, cambios de rol y desactivaciones concurrentes.

## 5. Hallazgos frontend / UX

La base visual es consistente: `AppShell`, `PageLayout`, componentes compartidos y tokens reducen variaciones entre módulos. Existen estados de carga, vacío y error, formularios con labels y mecanismos de foco y Escape en los componentes revisados. La nomenclatura predominante se orienta a pedidos, piezas, vidrios y existencias. La vista 3D conserva dimensiones originales y utiliza profundidad ilustrativa, sin convertirse en un segundo motor de cálculo.

### S1-10 — Acciones de Pedidos visibles sin el permiso correspondiente

- **Severidad:** MEDIUM.
- **Clasificación:** defecto confirmado por inspección estática.
- **Área:** Pedidos y contrato de autorización en UI.
- **Archivo:** `frontend/src/features/orders/GestionPedidos.jsx:183`.
- **Evidencia:** Nuevo, editar y cancelar no verifican individualmente los permisos de creación, edición y cancelación; el acceso al módulo se apoya en el permiso de visualización.
- **Riesgo:** un trabajador puede completar un formulario y recibir un 403 al enviarlo. El backend conserva la protección; no se trata de una evasión de autorización.
- **Solución recomendada:** condicionar cada acción a su permiso y mantener el detalle en modo de lectura cuando corresponda.
- **Esfuerzo aproximado:** 0,5–1 día.
- **SPEC / ADR / migración:** precisar interacción en SPEC; ADR no; migración no.
- **Pruebas necesarias:** usuario de solo lectura y combinaciones parciales de permisos, incluyendo respuestas 403 por permisos revocados durante la sesión.

### S1-11 — Cierre del modal de Pedidos puede perder el borrador

- **Severidad:** MEDIUM.
- **Clasificación:** defecto confirmado por inspección estática.
- **Área:** formularios y modales de Pedidos.
- **Archivos:** `frontend/src/features/orders/GestionPedidos.jsx:114` y `:153`; `frontend/src/features/orders/FormularioPedido.jsx:582`.
- **Evidencia:** Cancelar dentro del formulario dispone de confirmación, pero el cierre desde la X o Escape del contenedor utiliza otro camino que protege el envío en curso, sin aplicar la misma comprobación de cambios pendientes.
- **Riesgo:** pérdida accidental de un pedido o de cambios en piezas, medidas y cliente.
- **Solución recomendada:** unificar el cierre del modal con la comprobación de borrador modificado, sin rediseñar el formulario.
- **Esfuerzo aproximado:** 0,5–1 día.
- **SPEC / ADR / migración:** SPEC breve de interacción; ADR no; migración no.
- **Pruebas necesarias:** X, Escape y Cancelar con formulario limpio, modificado y enviándose; comprobar foco tras aceptar o rechazar el cierre.

### S1-20 — Contraste insuficiente en una combinación de texto secundario

- **Severidad:** LOW.
- **Clasificación:** mejora de accesibilidad con riesgo localizado.
- **Área:** estilos compartidos.
- **Archivo:** `frontend/src/shared/components/ui.css:54` y `:102`, junto con los tokens de color aplicados.
- **Evidencia:** el color `#64748b` alcanza aproximadamente 4,759:1 sobre blanco, pero 4,434:1 sobre `#f5f7fa`. La segunda combinación no alcanza el umbral 4,5:1 para texto normal; no corresponde redondearla a 4,5. Véase [WCAG 2.2: contraste mínimo](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html).
- **Riesgo:** dificultad de lectura del texto secundario donde se aplique esa combinación. No se extrapola el resultado a toda la interfaz.
- **Solución recomendada:** medir el fondo efectivo y oscurecer únicamente las combinaciones afectadas.
- **Esfuerzo aproximado:** 2–4 horas.
- **SPEC / ADR / migración:** no / no / no.
- **Pruebas necesarias:** contraste calculado sobre estilos efectivos y revisión visual de los componentes afectados.

### S1-21 — Filtros diarios dependen de zonas horarias diferentes

- **Severidad:** MEDIUM.
- **Clasificación:** riesgo temporal sustentado por implementación.
- **Área:** fechas y filtros de Pedidos.
- **Archivos:** `backend/app/modules/orders/infrastructure/repositories.py:113`; `frontend/src/features/orders/GestionPedidos.jsx:22`.
- **Evidencia:** el backend convierte timestamps a fecha según la sesión de BD, mientras que el frontend construye fechas con la zona local del navegador. Las pruebas revisadas usan UTC. Un pedido de la noche del día 18 en Lima puede corresponder al día 19 en UTC.
- **Riesgo:** pedidos que no aparecen bajo el día esperado por el trabajador.
- **Solución recomendada:** definir la zona operativa y traducir el día seleccionado a un intervalo explícito de timestamps.
- **Esfuerzo aproximado:** 0,5–1 día.
- **SPEC / ADR / migración:** SPEC sí; ADR no; migración no.
- **Pruebas necesarias:** medianoche, zona Lima, navegador en otra zona y límites inclusivo/exclusivo del intervalo.

### Evaluación funcional adicional

- **Cliente:** la selección permite búsqueda por nombre/documento y contempla interacción de teclado. Debe conservarse la selección y el borrador al corregir otros campos.
- **Grupos por material:** se implementa agrupamiento por vidrio y espesor y se evita duplicar la combinación en el formulario.
- **Piezas:** rectangulares, circulares y personalizadas están representadas; las unidades se expresan en milímetros. El editor muestra medidas y ángulos de forma progresiva, distinguiendo estados provisionales.
- **Optimización:** la selección de pedidos y la presentación por material utilizan el contrato del backend. La confirmación está condicionada por el resultado y el estado; el problema principal es la recuperación del flujo, descrita en S1-01 y S1-03.
- **Vistas 2D y 3D:** utilizan la solución recibida y sus dimensiones. No se encontró un First Fit productivo duplicado en React.
- **Responsive y accesibilidad:** hay estilos adaptativos y mecanismos de navegación/foco. Falta una pasada visual explícita a 390 px, con zoom y solo teclado para certificar el comportamiento completo de tablas, filtros y modales.
- **Clientes como experiencia:** la integración en los flujos existentes no justifica por sí sola crear una pantalla independiente.

No se recomienda un rediseño general de Usuarios, Inventario, Clientes, Pedidos, Optimización o Dashboard.

## 6. Hallazgos de optimización

### S1-01 — Previsualización histórica bloquea la ejecución First Fit

- **Severidad:** BLOCKER.
- **Clasificación:** defecto de integración confirmado.
- **Área:** estados de pedidos, endpoint histórico y ejecución.
- **Archivos:** `backend/app/modules/optimization/application/use_cases.py:17`; `backend/app/modules/optimization/infrastructure/run_uow.py:20`; `frontend/src/features/optimization/useOptimization.js:152`.
- **Evidencia:** el flujo histórico `/start` cambia los pedidos a `EN_OPTIMIZACION` sin crear una ejecución First Fit. El flujo `/runs` exige `PENDIENTE`. Se reprodujo la secuencia previsualización → First Fit → `STATE_CONFLICT`; el pedido tampoco queda habilitado para edición o cancelación ordinaria y falta una salida normal del estado.
- **Riesgo:** un flujo permitido por la aplicación puede dejar pedidos bloqueados antes de producir un resultado confirmable.
- **Solución recomendada:** convertir la previsualización en una operación sin transición de estado o integrarla explícitamente en el ciclo de vida de la ejecución. Revisar consumidores antes de retirar la ruta histórica y prever reconciliación autorizada de estados existentes.
- **Esfuerzo aproximado:** 1–2 días.
- **SPEC / ADR / migración:** SPEC sí; ADR no; migración no necesariamente, aunque puede requerirse reconciliación de datos existentes.
- **Pruebas necesarias:** secuencia completa previsualizar → ejecutar First Fit → consultar resultado → confirmar; compatibilidad con consumidores históricos y recuperación de pedidos atrapados.

### S1-02 — No existe un presupuesto global de trabajo de optimización

- **Severidad:** BLOCKER.
- **Clasificación:** riesgo de disponibilidad con ausencia de límites confirmada.
- **Área:** preparación del problema, stock, rasterización y concurrencia.
- **Archivos:** `backend/app/modules/orders/presentation/schemas.py:22`; `backend/app/modules/optimization/presentation/run_schemas.py:34`; `backend/app/modules/optimization/domain/preparation.py:37`; `backend/app/modules/optimization/infrastructure/stock_adapter.py:41`; `backend/app/modules/optimization/presentation/run_stream.py:126`.
- **Evidencia:** se acepta una cantidad de `2147483647`; la preparación expande piezas por cantidad antes de que los límites por objeto de rasterización puedan proteger el proceso. También se expanden unidades físicas de stock. No se encontró un límite operativo conjunto de pedidos, piezas expandidas, candidatos, vértices o ejecuciones simultáneas. La caché y los límites de layout por cálculo no resuelven ese costo acumulado. Se verificó la aceptación del valor extremo sin intentar materializar esa asignación masiva.
- **Riesgo:** una solicitud válida puede agotar CPU o memoria del monolito. Varias ejecuciones simultáneas agravan el problema.
- **Solución recomendada:** comprobar límites antes de expandir; fijar máximos de pedidos, piezas totales, unidades candidatas y vértices; acotar la admisión concurrente; evitar expandir stock innecesario e incorporar cancelación cooperativa y presupuesto temporal donde corresponda.
- **Esfuerzo aproximado:** 2–4 días.
- **SPEC / ADR / migración:** SPEC sí; ADR no; migración no para una primera solución.
- **Pruebas necesarias:** fronteras exactas de límites, rechazo previo a asignaciones grandes, concurrencia admitida/rechazada, stock voluminoso y geometría de peor caso.

### S1-03 — Recuperación incompleta de ejecuciones fallidas o no confirmables

- **Severidad:** HIGH.
- **Clasificación:** deuda técnica explícita con comportamiento confirmado.
- **Área:** ejecución, persistencia, navegación y recuperación operacional.
- **Archivos:** `backend/app/modules/optimization/infrastructure/run_uow.py:156`; `backend/app/modules/optimization/presentation/run_stream.py:95`; `frontend/src/features/optimization/useFirstFit.js:22`; `frontend/src/features/optimization/OptimizationPage.jsx:53`.
- **Evidencia:** una ejecución `FALLIDA` puede dejar pedidos en `EN_OPTIMIZACION` sin una API de reconciliación. Un resultado `OPTIMIZADO` cuyo stock ya no está disponible tampoco tiene un recorrido completo para volver a ejecutarse. El desmontaje del componente aborta la conexión; cambiar de herramienta puede interrumpir el flujo. Preparar otra optimización limpia estado local, pero no libera automáticamente los pedidos. La documentación reconoce parte de esta recuperación como diferida.
- **Riesgo:** pedidos retenidos y necesidad de intervención manual después de fallos, navegación o cambios legítimos de stock.
- **Solución recomendada:** recuperación autorizada y atómica que compruebe que no hubo consumo; conservar la referencia de ejecución y advertir antes de abandonar un trabajo activo. No restablecer estados automáticamente sin comprobar el resultado transaccional.
- **Esfuerzo aproximado:** 2–4 días.
- **SPEC / ADR / migración:** SPEC sí; ADR opcional; migración según el registro de recuperación elegido.
- **Pruebas necesarias:** desconexión, reinicio del proceso, fallo de persistencia, conflicto de stock y recuperación concurrente con confirmación.

### Invariantes del motor

| Invariante | Resultado de la revisión |
| --- | --- |
| Sin solapamientos | La colocación mediante máscaras y la reconstrucción revisada protegen contra solapamientos en la representación rasterizada. |
| Ninguna pieza fuera del material | Se utiliza una representación conservadora de la pieza y del interior utilizable del material. |
| Cantidad colocada correcta | Se conservan identidades y cantidades de piezas; la confirmación verifica la correspondencia del resultado. |
| Margen y separación | Se aplican mediante erosión/dilatación y redondeo conservador al rasterizar. |
| Determinismo | El ordenamiento y los datos del snapshot permiten resultados reproducibles para el mismo problema y configuración. |
| Métricas de la solución mostrada | Proceden del resultado persistido, no de una nueva optimización en el frontend. |
| Simulación sin mutación de stock | Confirmado en código y pruebas seleccionadas; sí existe persistencia del flujo y sus estados. |
| Confirmación sin mutaciones parciales | La unidad de trabajo y las pruebas de rollback con PostgreSQL respaldan esta propiedad. |
| `SIN_SOLUCION` | Significa que la heurística no encontró solución con las condiciones aplicadas; no es una prueba matemática de inviabilidad. |
| Generación de retazos | La política actual conserva el mayor rectángulo residual por unidad utilizada. No representa todo el material residual geométricamente recuperable. |

Se revisaron preparación multipedido/multimaterial, First Fit, rotaciones, selección entre planchas y retazos, rasterización, máscaras, métricas, snapshots y confirmación. No se encontró evidencia que justifique reemplazar el motor durante Sprint 2.

La cobertura adicional prioritaria es: límites agregados y concurrencia; material candidato no soportado junto con candidatos válidos; navegación y reinicio durante una ejecución; y el recorrido histórico previsualización → First Fit.

El stream no emite necesariamente un heartbeat durante cada paso largo. Conviene medir el tiempo entre bytes con geometrías costosas y contrastarlo con los límites de Heroku: 30 segundos para la respuesta inicial y ventana posterior de 55 segundos que se reinicia con tráfico. Es un riesgo a medir, no un timeout observado en staging. Fuente: [Heroku Request Timeout](https://devcenter.heroku.com/articles/request-timeout).

## 7. Hallazgos de base de datos y arquitectura relacionada

### S1-08 — Precisión de la API incompatible con `NUMERIC(10,2)`

- **Severidad:** MEDIUM.
- **Clasificación:** defecto confirmado.
- **Área:** dimensiones de inventario y contrato de persistencia.
- **Archivos:** `backend/app/models.py:133`; `backend/app/modules/inventory/presentation/schemas.py:120`; `backend/app/modules/inventory/application/service.py:90`; `backend/app/modules/inventory/infrastructure/repository.py:271`.
- **Evidencia:** se reprodujo un valor `1.234` respondido como `1.234` y almacenado como `1.23`. Un valor `0.001`, aceptado por la validación de positividad, produjo `IntegrityError` al convertirse a la precisión de la columna y violar la restricción.
- **Riesgo:** respuestas distintas de lo persistido y errores internos para entradas aceptadas por el contrato HTTP.
- **Solución recomendada:** definir precisión y rango canónicos, normalizar o rechazar explícitamente antes de persistir y devolver el mismo valor que se almacena.
- **Esfuerzo aproximado:** 0,5–1 día.
- **SPEC / ADR / migración:** SPEC sí; ADR no; migración no si se conserva la precisión actual.
- **Pruebas necesarias:** redondeo, valores que se convierten en cero, límites numéricos y consistencia entre POST, PATCH y GET.

### S1-15 — Lecturas completas y consultas que deben medirse

- **Severidad:** MEDIUM.
- **Clasificación:** deuda de rendimiento; no se ha demostrado degradación en producción.
- **Área:** consultas, payloads, índices y Dashboard.
- **Archivos:** `backend/app/modules/optimization/infrastructure/stock_adapter.py:27`; `backend/app/modules/inventory/infrastructure/repository.py:284`; `backend/app/modules/clients/infrastructure/sqlalchemy_client_repository.py:48`; `backend/app/modules/orders/infrastructure/repositories.py`; `frontend/src/features/dashboard/dashboardApi.js`.
- **Evidencia:** se cargan planchas y retazos completos por grupo de material y se filtran en Python; hay listados completos de inventario, clientes y usuarios; el Dashboard obtiene colecciones para calcular indicadores; el frontend solicita detalles individuales por pedido. No se encontró índice sobre `piezas.id_pedido` ni uno específico para ciertas consultas de movimientos por optimización.
- **Riesgo:** trabajo proporcional al historial completo o al número de grupos, más solicitudes por pedido y mayor transferencia de datos. Una FK por sí sola no demuestra que exista el índice útil para la consulta.
- **Solución recomendada:** medir planes, tiempos, cantidad de consultas y payloads con datos representativos. Después, filtrar en SQL, paginar o agregar índices solo donde la medición lo justifique.
- **Esfuerzo aproximado:** 1 día de medición y 1–2 días para correcciones acotadas.
- **SPEC / ADR / migración:** SPEC para cambios de paginación/contrato; ADR no; migración solo para índices justificados.
- **Pruebas necesarias:** presupuestos de consultas/payload, volumen representativo y planes antes/después; evitar assertions dependientes de un plan exacto del optimizador SQL.

### S1-16 — Reglas geométricas diferentes entre Pedidos e Inventario

- **Severidad:** MEDIUM.
- **Clasificación:** deuda de contrato con discrepancia confirmada.
- **Área:** geometría de piezas y retazos.
- **Archivos:** `backend/app/modules/orders/domain/geometry.py:34`; `backend/app/modules/inventory/domain/geometry.py:67`; validación de convexidad del frontend.
- **Evidencia:** un rectángulo con un vértice colineal adicional es aceptado por Pedidos con área 100 y rechazado por Inventario. El frontend también trata determinados casos colineales de forma diferente. Existen diferencias de tolerancia y tratamiento numérico.
- **Riesgo:** geometrías aceptadas en un flujo y rechazadas al reutilizarlas en otro, con mensajes difíciles de explicar al trabajador.
- **Solución recomendada:** acordar el contrato geométrico y un conjunto compartido de ejemplos. Extraer funciones puras comunes solo si las reglas deben ser realmente iguales; documentar diferencias deliberadas.
- **Esfuerzo aproximado:** 1–2 días.
- **SPEC / ADR / migración:** SPEC sí; ADR solo si se decide propiedad compartida entre dominios; migración no.
- **Pruebas necesarias:** vértices colineales, traslación, escala, orientación, tolerancias y cuantización de áreas.

### S1-17 — Duplicación y concentración de responsabilidades en puntos de cambio

- **Severidad:** MEDIUM.
- **Clasificación:** deuda arquitectónica concreta, no preferencia estilística.
- **Área:** validación de pedidos y coordinación de formularios/inventario.
- **Archivos:** `backend/app/modules/orders/application/use_cases.py`; `frontend/src/features/inventory/InventoryPage.jsx`; `frontend/src/features/orders/FormularioPedido.jsx`; `frontend/src/features/orders/CustomPieceEditor.jsx`.
- **Evidencia:** creación y edición de pedidos duplican validaciones de piezas. `InventoryPage` concentra aproximadamente 940 líneas, `FormularioPedido` 634 y `CustomPieceEditor` 503. El problema no es el número por sí mismo: inventario coordina edición, bajas, historial y estados asíncronos que afectan a S1-04, S1-05 y S1-09.
- **Riesgo:** aplicar una regla en creación pero no en edición, o corregir un flujo de inventario dejando otro con comportamiento diferente.
- **Solución recomendada:** extraer validación común de piezas y separar la coordinación de baja/historial cuando se implementen los cambios funcionales relacionados. Evitar un refactor masivo sin requisito.
- **Esfuerzo aproximado:** 1–3 días, parcialmente solapados con los hallazgos funcionales.
- **SPEC / ADR / migración:** SPEC no necesariamente; ADR no; migración no.
- **Pruebas necesarias:** equivalencia de creación/edición y comportamiento asíncrono de los flujos extraídos.

### Evaluación estructural de BD

- Hay claves foráneas, restricciones, unicidad y reglas de exclusión para distinguir orígenes de material.
- La evolución a multipedido incluye tratamiento de datos anteriores; no corresponde retirar relaciones históricas sin revisar consumidores y datos.
- El uso de JSONB para snapshots versionados es razonable: conserva la solución utilizada sin exigir recalcularla.
- Configuración, ejecución, material utilizado, métricas y origen de retazos cuentan con representación persistente y trazabilidad.
- La presencia de más de una configuración vigente se trata como `CONFIG_CONFLICT`; el bootstrap utiliza bloqueo para su coordinación.
- Un ciclo entre relaciones del esquema no equivale a una dependencia circular de importaciones ni demuestra por sí mismo un defecto.
- No hay motivo demostrado para sustituir JSONB o normalizar todos sus campos.
- La revisión cubrió modelos y migraciones del repositorio; no certifica que una base compartida tenga aplicada exactamente esa revisión.

## 8. Pruebas, CI/CD, configuración y repositorio

### S1-07 — CI puede omitir E2E previstos por falta de configuración

- **Severidad:** HIGH.
- **Clasificación:** defecto confirmado en configuración y condiciones de ejecución.
- **Área:** GitHub Actions y Playwright.
- **Archivos:** `.github/workflows/ci.yml`; E2E de HU-015; `frontend/tests/e2e/ta-dashboard.spec.js:14`; configuración E2E asociada.
- **Evidencia:** hay pruebas condicionadas a variables de entorno que ejecutan `skip` si no están presentes. El workflow y la configuración principal no proporcionan todos esos valores. Definirlos dentro del proceso servidor hijo no los incorpora al entorno del proceso padre que evalúa los tests. La prueba estática del workflow no detecta esta omisión funcional.
- **Riesgo:** pipeline verde sin ejecutar recorridos previstos de confirmación y Dashboard.
- **Solución recomendada:** centralizar identidades sintéticas y configuración; hacer fallar CI ante configuración requerida ausente y ante skips no autorizados.
- **Esfuerzo aproximado:** 0,5–1 día.
- **SPEC / ADR / migración:** no / no / no.
- **Pruebas necesarias:** ejecución con configuración completa, fallo explícito con configuración ausente y comprobación de tests ejecutados/skips admitidos.

### S1-18 — Documentación operativa con referencias obsoletas

- **Severidad:** LOW.
- **Clasificación:** deuda documental.
- **Área:** incorporación, staging y evidencia.
- **Archivos:** `CONTRIBUTING.md`; `docs/infrastructure/staging.md`; `frontend/src/features/README.md`; documentos de revisión y evidencia de Sprint 1.
- **Evidencia:** persisten referencias a First Fit como fuera de Sprint 1, instrucciones o SHA históricos de staging, referencias a `src/pages` retirado e indicaciones antiguas de seed/bootstrap. Se contabilizaron 401 archivos de evidencia; su existencia no demuestra que el HEAD actual cumpla cada comportamiento.
- **Riesgo:** seguir instrucciones antiguas o confundir evidencia histórica con validación vigente.
- **Solución recomendada:** mantener una sección operativa actual con SHA, comandos, límites y enlaces a evidencia histórica. Conservar la historia útil sin presentarla como estado vigente.
- **Esfuerzo aproximado:** 0,5–1 día.
- **SPEC / ADR / migración:** no / no / no.
- **Pruebas necesarias:** comprobación de rutas, enlaces y coherencia entre instrucciones y configuración; no requiere desplegar para corregir documentación.

### S1-19 — Promoción a `main` afectada por merge revertido

- **Severidad:** HIGH para la futura promoción.
- **Clasificación:** riesgo de release confirmado en el historial local visible.
- **Área:** estrategia de ramas y revisión del árbol final.
- **Referencias:** merge del PR #52 `bc2ee37`; revert `841279d`; PR #53 y `main` en `9a890d1`; PR #54 e integración en `9546993`; ancestro común `7f59cb3`.
- **Evidencia:** el árbol de `main` corresponde al estado previo al PR #52. El árbol de integración coincide con contenido ya incluido en la historia común, aunque `main` lo haya revertido. Git conserva la ascendencia del merge: un merge ordinario no garantiza reintroducir el contenido revertido. Véase [documentación de git revert](https://git-scm.com/docs/git-revert).
- **Riesgo:** una promoción aparentemente correcta puede omitir funcionalidad de Sprint 1 o producir una revisión engañosa del diff.
- **Solución recomendada:** preparar una promoción explícita y autorizada, evaluando revertir el revert u otra estrategia revisable y comprobando el árbol final completo, compatibilidad de BD y gates de release. Esta auditoría no repara el historial.
- **Esfuerzo aproximado:** 0,5–1 día de preparación más validación de release.
- **SPEC / ADR / migración:** SPEC no; ADR opcional o procedimiento documentado de release; migración no por el historial en sí.
- **Pruebas necesarias:** comparación del árbol esperado, suite de release y smoke del candidato final.

### Calidad y distribución de pruebas

- La separación entre unitarias, integración, API, componentes y E2E es aprovechable. Deben conservarse las pruebas de transacciones y bloqueos con PostgreSQL real.
- Las fixtures SQLite que eliminan o adaptan restricciones no demuestran integridad PostgreSQL. Su utilidad debe limitarse al comportamiento que realmente modelan.
- Los mocks de componentes no descubren por sí solos la incompatibilidad previsualización → First Fit ni la pérdida de respuesta después del commit.
- No se encontró una razón para eliminar pruebas en masa por aparente duplicación: varias verifican límites distintos. Conviene revisar duplicaciones al cambiar el flujo correspondiente.
- Hay assertions acopladas al copy, al número exacto de solicitudes o a la estructura textual del workflow. Deben complementarse o reemplazarse selectivamente por comportamiento observable cuando impidan una evolución legítima.
- Los benchmarks revisados cubren escenarios concretos, pero no sustituyen pruebas de peor caso y concurrencia agregada de S1-02.
- E2E debe concentrarse en recorridos completos, autenticación real de navegador y contratos entre módulos. Geometría y combinaciones extensas de error encajan mejor en unitarias o componentes.
- No se recomienda cambiar dependencias únicamente por advertencias de deprecación sin evaluar impacto y requisito.

### Configuración, secretos y despliegue

- En el árbol versionado revisado se encontraron archivos de ejemplo de entorno, sin una evidencia positiva de claves privadas o secretos JWT productivos. Esto no equivale a un escaneo de toda la historia Git.
- No se expusieron valores del `.env` durante el informe. Su presencia local no demuestra que esté versionado.
- La configuración CORS revisada usa orígenes explícitos, sin un wildcard general para resolver staging.
- La configuración de staging contempla HTTPS y el subpath de GitHub Pages. `VITE_API_URL` debe corresponder al backend desplegado y a los orígenes permitidos; no se certificaron las variables remotas actuales.
- Los health checks distinguen disponibilidad básica y dependencia de BD; la comprobación revisada tiene un límite temporal de tres segundos y evita acumular trabajo indefinidamente.
- Hay comprobaciones de build para Pages. El `Procfile` de Heroku no ejecuta migraciones automáticamente.
- No se verificaron en remoto protecciones de rama, TLS efectivo, grants/RLS de Supabase ni Config Vars. Deben comprobarse sobre el candidato de release, sin asumir que el repositorio demuestra su estado actual.

## 9. Deuda técnica priorizada

Los esfuerzos son aproximados para una persona con conocimiento del repositorio e incluyen validación acotada. Hay solapamientos: no deben sumarse mecánicamente.

| ID | Severidad | Clasificación | Área | Trabajo prioritario |
| --- | --- | --- | --- | --- |
| S1-01 | BLOCKER | Defecto confirmado | Optimización | Resolver incompatibilidad entre previsualización y ejecución. |
| S1-02 | BLOCKER | Riesgo confirmado por ausencia de controles | Disponibilidad | Limitar trabajo antes de expandir piezas/stock y admitir ejecuciones. |
| S1-03 | HIGH | Deuda técnica | Optimización | Recuperación de ejecuciones y pedidos retenidos. |
| S1-04 | HIGH | Defecto confirmado | Inventario | Impedir reactivación/baja de retazos consumidos. |
| S1-05 | HIGH | Deuda técnica | Inventario | Registrar ajustes manuales de stock. |
| S1-06 | HIGH | Defecto confirmado | RBAC | Preservar roles deliberadamente sin permisos. |
| S1-07 | HIGH | Defecto de configuración | CI/E2E | Evitar skips silenciosos por variables ausentes. |
| S1-09 | HIGH | Riesgo | Mutaciones | Reintentos seguros después de respuestas ambiguas. |
| S1-14 | HIGH | Defecto y riesgo concurrente | Usuarios | Preservar capacidad administrativa activa. |
| S1-19 | HIGH | Riesgo de release | Git y promoción | Preparar promoción considerando el revert de `main`. |
| S1-08 | MEDIUM | Defecto confirmado | Contrato numérico | Alinear validación, respuesta y precisión persistida. |
| S1-10 | MEDIUM | Defecto de UX | Pedidos/RBAC | Mostrar acciones según permisos. |
| S1-11 | MEDIUM | Defecto de UX | Pedidos | Proteger el borrador en todos los cierres. |
| S1-12 | MEDIUM | Defecto confirmado | Errores | No devolver contraseñas en validación. |
| S1-13 | MEDIUM | Riesgo | Autenticación | Definir intentos y revocación. |
| S1-15 | MEDIUM | Deuda de rendimiento | Consultas/BD | Medir lecturas, payloads e índices candidatos. |
| S1-16 | MEDIUM | Deuda de contrato | Geometría | Acordar reglas y casos compartidos. |
| S1-17 | MEDIUM | Deuda arquitectónica | Aplicación/UI | Reducir duplicación y coordinación concentrada al tocar los flujos. |
| S1-21 | MEDIUM | Riesgo temporal | Pedidos | Definir zona operativa para filtros diarios. |
| S1-18 | LOW | Deuda documental | Documentación | Consolidar instrucciones vigentes. |
| S1-20 | LOW | Mejora de accesibilidad | UI | Ajustar combinaciones de contraste insuficiente. |

No se eleva una preferencia estilística a defecto. Tamaño de archivos, nombres, distribución de carpetas o elección de patrones solo justifican trabajo cuando se conectan con un riesgo funcional o de mantenimiento demostrado.

## 10. Mejoras recomendadas antes de Sprint 2

Los dos requisitos de entrada recomendados son:

1. **S1-01:** demostrar el recorrido completo desde selección/previsualización hasta ejecución y confirmación, sin pedidos atrapados por estados incompatibles.
2. **S1-02:** rechazar solicitudes que excedan el presupuesto antes de expandir piezas o stock y acotar la admisión de ejecuciones concurrentes.

Por su tamaño acotado y beneficio inmediato, conviene adelantar también S1-06, S1-07, S1-12 y S1-08: seed de permisos, E2E efectivos, saneamiento de errores y precisión numérica.

La recuperación operacional, la trazabilidad de inventario y los reintentos seguros deben entrar con prioridad explícita al inicio de Sprint 2. No conviene diluirlos dentro de una tarea genérica de refactor.

## 11. Mejoras que pueden esperar

- Paginación de usuarios si el volumen sigue siendo pequeño y las mediciones no muestran impacto.
- Optimización de lecturas de roles de cardinalidad reducida, sin un costo demostrado.
- Extracción de componentes no relacionados con los defectos priorizados.
- Reorganización física de modelos únicamente por preferencia de carpetas.
- Búsqueda y administración avanzada de ejecuciones una vez resuelto su ciclo de recuperación básico.
- Más automatización de despliegue antes de estabilizar los gates y el procedimiento de promoción.
- Algoritmos más sofisticados o recuperación de múltiples retazos por unidad, salvo que un requisito de aprovechamiento lo justifique.

Los cambios de índices y estructura de datos deben esperar a mediciones o necesidades demostrables; no a una presunción de que más índices o más tablas mejoran el sistema.

## 12. Cosas que expresamente NO conviene cambiar

| ID | Severidad | Área | Observación y recomendación |
| --- | --- | --- | --- |
| NA-01 | NO ACTION | Arquitectura | Mantener FastAPI como monolito modular, React y PostgreSQL. La inspección y `docs/adr/ADR-001-seleccion-arquitectura.md` no justifican reemplazarlos. |
| NA-02 | NO ACTION | Consistencia | Preservar la unidad de trabajo y los bloqueos de `run_uow.py` y `confirmation_adapter.py`; no repartir la confirmación en commits independientes por módulo. |
| NA-03 | NO ACTION | Motor | Mantener máscaras, determinismo, métricas persistidas y reconstrucción desde snapshot. No duplicar First Fit en React. |
| NA-04 | NO ACTION | Persistencia | Conservar JSONB versionado e historia en `run_snapshot.py` y los modelos relacionados; no retirar campos sin revisar consumidores y datos existentes. |
| NA-05 | NO ACTION | Alcance | No implementar módulos o abstracciones solo porque exista una carpeta preparada para ellos. |
| NA-06 | NO ACTION | Evidencia | No eliminar masivamente `docs/evidence`; mejorar su índice, procedencia y distinción entre evidencia histórica y vigente. |
| NA-07 | NO ACTION | Infraestructura | No introducir por defecto microservicios, Redis, Celery, WebSockets, Kubernetes, CQRS o Event Sourcing. No hay evidencia suficiente de necesidad. |

**Clasificación:** observaciones válidas que no justifican cambio. **Esfuerzo:** 0. **SPEC / ADR / migración:** no se requiere un cambio por estas observaciones. **Pruebas:** conservar las garantías existentes al implementar los hallazgos funcionales. El riesgo de ignorar estas recomendaciones es añadir complejidad sin resolver los problemas encontrados.

## 13. Propuesta de Enablers técnicos para Sprint 2

| Enabler | Hallazgos relacionados | Resultado verificable |
| --- | --- | --- |
| **EN-S2-01 — Ciclo de vida y recuperación de optimización** | S1-01, S1-03 | La previsualización no bloquea la ejecución; existe recuperación autorizada; un fallo o conflicto no deja pedidos sin salida operacional. |
| **EN-S2-02 — Presupuesto de ejecución del motor** | S1-02 | Límites previos a expansión, admisión acotada, cancelación cooperativa donde corresponda y benchmark de peor caso. |
| **EN-S2-03 — Trazabilidad e idempotencia de inventario** | S1-04, S1-05, S1-09 | Un retazo consumido no vuelve a estar disponible; cada ajuste queda auditado; repetir una identidad de operación no duplica efectos. |
| **EN-S2-04 — RBAC, errores sensibles y sesiones** | S1-06, S1-10, S1-12, S1-13, S1-14 | El seed preserva permisos administrados; UI coherente; errores sin credenciales; política de sesiones y protección de capacidad administrativa. |
| **EN-S2-05 — Contrato geométrico y numérico** | S1-08, S1-16 | Precisión coherente entre API y BD, reglas geométricas explícitas y corpus de casos compartidos. |
| **EN-S2-06 — Gates y promoción de release** | S1-07, S1-18, S1-19 | Sin skips silenciosos, documentación operativa vigente y promoción cuyo árbol final se verifica considerando el revert. |
| **EN-S2-07 — Medición y diagnóstico operativo** | S1-15 | Medición de SQL, payloads y tiempos con datos representativos; correlación de errores/ejecuciones sin registrar datos sensibles. |
| **EN-S2-08 — Robustez de formularios y fechas** | S1-11, S1-20, S1-21 | Borradores protegidos, contraste suficiente en casos afectados y filtros diarios coherentes con la zona operativa. |

La auditoría no aplicó correcciones, autofix, cambios de dependencias, commits, push, PR ni migraciones sobre bases compartidas. La autorización posterior se limita a crear este documento; cualquier corrección requiere una nueva autorización.
