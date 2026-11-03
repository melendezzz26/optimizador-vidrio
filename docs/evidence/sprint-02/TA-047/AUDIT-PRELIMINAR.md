# TA-047: auditoría preliminar

Autor y revisor académico asignado: Andro Joseph Quispe Cesias. No consta aprobación de GitHub.

Base: `origin/integration/sprint-01` en `7556a700496673d00fe41b6036d69d91d0939959`. Estado inicial: rama SP-005 y `experiments/sp-006-m6/` no rastreado. El experimento se conservó fuera de los cambios.

El endpoint `/runs` llama a `AcceptRun`: valida selección, configuración, cantidades, geometría y presupuesto, prepara el problema y crea la ejecución. `CalculateRun` consulta el stock después y ejecuta First Fit. La comparación usa `AcceptComparison`, que captura el stock y prepara el problema antes de crear sus registros; su ruta de cálculo es independiente. Por tanto no hay un punto existente común después de capturar stock y antes de persistir ambas clases de ejecución. La integración comparativa requiere coordinación con TA-043; no se modificó ese flujo.

La preparación valida piezas persistidas y cantidades. `geometry_snapshot` admite rectángulo, circunferencia y polígono convexo; las validaciones de pedidos son responsables de la geometría de origen. El núcleo preliminar usa `RasterCache`, orientaciones discretas y `_empty_layout`/`first_position`: el margen erosiona la fuente y la separación solo afecta a piezas ya colocadas. Esto comprueba posiciones individuales, no construye soluciones completas. Los errores de recursos se propagan en lugar de declararse como imposibilidad geométrica.

Estado: **incompleto**. El núcleo todavía no está conectado a las rutas; faltan respuesta API, pruebas completas, mediciones, regresiones, SPEC, PLAN, TASKS y revisión. Las tres pruebas preliminares de `test_preflight.py` pasaron con el entorno virtual local. No hay evidencia para declarar los criterios de aceptación completos.
