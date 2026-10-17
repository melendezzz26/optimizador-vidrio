# Tareas — Auditoría y hardening de Optimización S1

Fecha: 2026-10-17. [AUDIT](AUDIT-S1-OPTIMIZATION-UX.md) · [PLAN](PLAN-S1-OPTIMIZATION-UX.md).
No se ha iniciado la implementación; los checks documentales no significan
validación autenticada de staging ni correcciones realizadas.

## Fase entregada

- [x] Verificar rama obligatoria, árbol inicial limpio, fetch e integration.
- [x] Trazar flujo real, fixtures, contratos, stock, agrupación, raster y confirmación.
- [x] Revisar shell/permisos y consistencia con módulos vecinos por código.
- [x] Ejecutar unit/component/lint/build con Node portable existente.
- [x] Recorrer frontend en Chrome desktop/mobile con HTTP controlado.
- [x] Reproducir grupos vacíos y carreras de recuperación/confirmación.
- [x] Localizar URLs documentadas y comprobar login público, assets y API health/OpenAPI.
- [x] Buscar autenticación reutilizable documentada; registrar que las cuentas existentes son locales efímeras.
- [x] Clasificar P0/P1/P2/P3 y separar A/B/C/D con evidencia y límites.
- [x] Redactar plan y criterios de aceptación antes de modificar producto.
- [ ] Recorrer flujo autenticado de staging: pendiente de sesión/cuenta de prueba documentada y datos autorizados.
- [ ] Reejecutar E2E de motor real: runner no disponible por dependencias y no autorizado para crear BD en esta fase.

## Implementación futura A — no realizada

- [ ] T01 / AU-03: regresión de recuperación tardía tras nueva selección/preparación; invalidación coherente.
- [ ] T02 / AU-04: regresión de POST confirm pendiente; bloqueo de acciones y reconciliación por ID.
- [ ] T03 / AU-02: selector persistente para grupos sin contenedor; navegación 2D/3D entre grupos.
- [ ] T04 / AU-06: diagnóstico canónico de unidades no colocadas, cantidades y motivos.
- [ ] T05 / AU-01/05/07/09: advertencias/estados precisos del flujo heredado, raster, cierre local y resumen.
- [ ] T06 / AU-05: resolución real en resultado recuperado, sin fabricar máscara ni parámetros.
- [ ] T07 / AU-08: límite de cámara ±90 y regresión por pointer/teclado/ARIA, sin mutar placements.
- [ ] T08 / AU-10: leyenda consolidada y controles móviles, manteniendo accesibilidad.
- [ ] T09: unit/component/lint/build completos después de cambios.
- [ ] T10: navegador desktop/mobile, reduced motion, zoom/pan, foco, HTTP y evidencia antes/después.
- [ ] T11: E2E real bajo entorno permitido; reportar pendiente si sigue sin existir.
- [ ] T12: revisión diff/check, commits por bloque, push de feature y estado final de integration.

## Dependencias que no se deben marcar como resueltas por UI

- [ ] B01 / AU-01: contrato backend de preview sin cambiar estado o convergencia HU-015/runs.
- [ ] B02 / AU-05: máscaras de corrida para inspección reproducible de contactos y contenedores.
- [ ] C01 / AU-01: decisión de negocio sobre continuidad/salida del flujo heredado.
- [ ] C02 / AU-07: semántica de abandono/cancelación y recuperación de pedidos.
- [ ] C03: política de configuración de raster por corrida y entorno/datos de prueba remotos.
- [ ] D01 / AU-11: actualización separada de guías obsoletas, conservando su historia.
