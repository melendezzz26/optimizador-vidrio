# PLAN TA-047 — Preflight de optimización

Autor y revisor académico: Andro Joseph Quispe Cesias. Sin aprobación de GitHub atribuida.

1. Reutilizar contratos de pedido, stock, raster, rotación y margen; devolver errores deterministas por pieza.
2. Ejecutar el control de la corrida individual antes de `runs.create` sin modificar la comparación.
3. Validar geometrías, material, espesor, lectura sin mutación, rechazo sin persistencia y regresiones disponibles.
4. Tras TA-043, integrar el mismo control en la aceptación comparativa antes de crear el snapshot y ejecuciones, y comprobar respuesta, efectos y paridad de los seis métodos. No duplicar la implementación.

La captura en `/runs` es una observación, no una reserva. El stock se vuelve a leer en `CalculateRun`; un cambio concurrente puede invalidar el resultado del preflight y el motor debe seguir manejándolo.
