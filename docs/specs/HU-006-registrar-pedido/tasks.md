# Tareas HU-006 — convergencia multimaterial

Estado general: Reviewed, implementación parcial; HU-006 no está Verified. El commit `80a4fa4` y su autoría permanecen sin reescritura. Esta fase implementa el contrato del backend y su evolución local de esquema; la pantalla aún conserva la restricción temporal de guardado y necesita integración con el backend nuevo.

- [x] Definir el contrato de material y espesor por pieza, las formas permitidas y el plan de preservación histórica.
- [x] Consolidar la pantalla mixta en `features/orders`, preservando CustomPieceEditor y bloquear temporalmente el guardado de pedidos mixtos hasta que el backend lo soporte.
- [x] Mantener dependencias HTTP en Presentation y evitar importaciones tempranas de BD.
- [x] Actualizar el modelo canónico, el schema HTTP, el caso de uso y el repositorio Orders para material por pieza.
- [x] Añadir migración descendiente de TA-013 y estrategia de downgrade que bloquea datos no representables sin pérdida.
- [x] Implementar `POST /api/orders` multimaterial y `GET /api/orders/{id_pedido}`.
- [x] Cubrir persistencia multimaterial, parejas repetidas, errores sin escrituras parciales, lectura, permisos y migración en PostgreSQL temporal.
- [ ] Completar la pantalla frontend para enviar el contrato multimaterial sin restricción temporal y validar el flujo visual/accesible.
- [ ] Aplicar la migración en un entorno objetivo tras revisión y coordinación; Supabase no se ha modificado en esta fase.
- [x] Ejecutar la regresión global del backend en PostgreSQL temporal y registrar el resultado (961 passed).
- [ ] Reunir evidencia integral HU-006, hacer revisión formal y entonces considerar Implemented/Verified.

## Verificación de backend de esta fase — 2026-10-08

| Suite específica | Resultado |
|---|---:|
| Migración multimaterial en PostgreSQL temporal | 13 passed |
| Orders Application unit tests | 34 passed |
| Orders repository integration | 6 passed |
| Orders API | 54 passed |
| Suite backend completa | 961 passed |

La regresión encontró tres aserciones de la suite TA-013 que aún trataban TA-013 como `head` y construían PEDIDO con el esquema antiguo. Se adaptaron para preservar la cobertura histórica y comprobar el rollback transaccional del downgrade en la cadena vigente; los tres casos específicos pasan y la suite completa finalizó con 961 passed. La migración de pruebas utiliza PostgreSQL aislado y no depende de datos manuales de Supabase. No se ejecutó frontend, ya que no hubo cambios compartidos de frontend en esta fase. Rasterización queda para Sprint 1; First Fit, Best Fit y Worst Fit quedan para Sprint 2.
