# Checklist para integrar TA-043 en `integration-02`

- [ ] Revisar esta matriz con Fabricio.
- [ ] Confirmar decisión sobre RF-20/HU-018.
- [ ] Confirmar que `integration-02` sigue en `d85a8d3c4fa2ba1b3f70c401ed947adcfbe2470b`.
- [ ] Comparar el diff completo de TA-043 contra `integration-02`.
- [ ] No incorporar PR #96–#100 sin revisión específica.
- [ ] Resolver conflictos de pedidos, inventario, frontend y contratos v1.
- [ ] Ejecutar pruebas de migración sobre una base privada de integración.
- [ ] Ejecutar regresiones v1, `/runs`, B09 y el validador B10 tras resolver conflictos.
- [ ] Confirmar que no cambian heurísticas, presupuestos ni concurrencia.
- [ ] Revisar secretos, variables de entorno y archivos temporales.
- [ ] Obtener aprobación formal de SPEC/PLAN.
- [ ] Abrir PR únicamente después de esta checklist.
- [ ] Antes de desplegar, validar Linux objetivo y mecanismos procfs/prctl/RLIMIT_AS.
- [ ] No declarar capacidad de 150 unidades sin una medición aprobada.

