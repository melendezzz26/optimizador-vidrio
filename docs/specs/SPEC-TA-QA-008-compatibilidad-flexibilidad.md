# SPEC TA-QA-008 - Compatibilidad y flexibilidad

Responsable: Andro Joseph Quispe Cesias. Reviewer: Fabricio Danniel Aguilar Chavez (fabrilar1). Base: integration-02.

## Problema y objetivo
Comprobar con flujos reproducibles y datos sinteticos locales el acceso y continuidad de interfaces y acciones principales en navegadores y viewports candidatos.

## Alcance
Login, pedidos, inventario, optimizacion, comparacion y navegacion principal, escritorio, tablet y movil emulado. Chrome y Edge instalados son candidatos de prueba; no se declara soporte de un navegador o dispositivo por una emulacion. Firefox no esta acordado. Fuera de alcance: evaluacion subjetiva visual, accesibilidad integral, rendimiento, produccion y redisenos amplios.

## Metricas y ambiente
MC-01: combinaciones exitosas / combinaciones evaluadas * 100. MC-02: pantallas sin perdida / pantallas evaluadas * 100. MC-03: flujos exitosos / flujos evaluados * 100. Denominador cero: no evaluable; informar combinaciones no ejecutadas por separado. Ver matriz TA-QA-001: esta rama corrige operadores corruptos durante migracion anterior. Pruebas con Playwright y Chrome/Edge reales en equipo local, frontend Vite y backend real con PostgreSQL temporal de loopback; no usar produccion.

## Criterios
CA-01 desktop; CA-02 movil; CA-03 controles esenciales sin desbordamiento inaccesible; CA-04 formularios completables; CA-05 acceso a tablas y acciones; CA-06 controles utilizables; CA-07 errores especificos de navegador; CA-08 navegacion operativa; CA-09 defectos documentados; CA-10 MC-01/02/03 con numerador, denominador y evidencia. No marcar como satisfechos si no se prueba el flujo completo. Riesgos: navegadores/versiones o servidor local no disponibles, emulacion distinta a dispositivo real, cambios concurrentes del equipo.
