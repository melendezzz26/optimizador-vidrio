# Ampliación 3D — evidencia técnica

Registro de la entrega f538eeb. El refinamiento posterior de grupos, planchas base e inspección raster está en [groups-raster.md](groups-raster.md); se conservan aquí las pruebas y decisiones de esta entrega histórica.

Fecha: 2026-10-15. Alcance exclusivo frontend y fixtures.

| Frente | Estado |
|---|---|
| SPEC | APPROVED |
| Frontend de optimización | COMPLETED WITH FIXTURES |
| Vista 2D | IMPLEMENTED |
| Vista 3D | IMPLEMENTED |
| Integración First Fit real | PENDING |
| Rotación automática real calculada por motor | PENDING |
| Confirmación persistente real | PENDING |

Fabricio Meléndez desarrolla e integrará posteriormente el motor y las rotaciones automáticas reales. Andro Q. deja preparada la UI y coordina su conexión con el motor. El frontend consume el contrato temporal de snapshot/eventos documentado en SPEC; aún deben acordarse sus detalles definitivos. No es una solución de producción Verified. El fixture no guarda ni descuenta inventario. `stage_changed` continúa siendo interno/opcional, nunca un requisito backend.

## Decisión e implementación

Proyección matemática 3D sobre SVG, sin librerías ni cambios de package/lock. Este alcance necesita inspeccionar geometría plana extruida, no un motor CAD/WebGL. Se separan `placementScene.js` (geometría/proyección), `PlacementScene3D.jsx` y su CSS (presentación/interacción), y `PlacementCanvas.jsx` (vista y contenedor compartidos). `OptimizationPage.jsx` reinicia la presentación solo al cambiar run_id.

Se utiliza la misma normalización del pivote, x_mm/y_mm/rotation_deg y geometría del snapshot que en 2D. Rectángulos y polígonos convexos conservan vértices; círculos se representan mediante 96 segmentos únicamente en el visor. Escala uniforme según dimensiones del material; perspectiva con cámara fija a 48° y yaw entre −90° y +90°. El encuadre permanece estable durante el giro, incluidas planchas cuadradas o alargadas. Profundidad y cantos son ilustrativos, no espesor físico a escala. No se resuelven colisiones, factibilidad, colocaciones ni ángulos óptimos.

Selector oculto hasta la primera colocación válida; 2D sigue siendo la referencia precisa. Alternar conserva contenedor, snapshot, métricas y progreso. La visualización admite aparición progresiva de piezas y mantiene identidad/color por unidad del snapshot. Paleta de seis colores reutilizable con identificación textual de pieza, pedido y unidad. Superficie libre visible sin inventar retazos. Grilla adaptativa de referencia en mm; no equivale a máscara raster. Se conserva el inspector RasterComparison de HU-015.

Mouse/touch horizontal mediante Pointer Events, captura/cancelación de puntero, flechas izquierda/derecha, Home/End y Restablecer vista (−24°). Control con rol slider, límites y valor accesibles. Inclinación fija, sin órbita libre ni movimiento automático; reduced-motion deshabilita transiciones. Móvil permite desplazamiento vertical de página. Conserva componentes y tokens de NewGlass.

## Validación real

Node portátil 24.15.0, npm 11.9.0. Desde frontend, Node en PATH:

| Comando | Resultado | Evidencia |
|---|---|---|
| npm run test:unit | 141 PASS, 0 fallos | [salida](3d-unit.txt) |
| npm run test:component | Suite completa: 351 PASS, 32 archivos | [salida](3d-component.txt) |
| npm run lint | exit 0 | [salida](3d-lint.txt) |
| npm run build | exit 0, JS 416.01 kB / gzip 125.74 kB | [salida](3d-build.txt) |
| npx playwright test --config playwright.optimization.config.js | 6 PASS, 34.4 s, desktop/mobile | [salida](3d-e2e.txt) |

E2E con `$env:OPTIMIZATION_E2E_PORT='5187'`; la configuración permite puerto alternativo conservando 5186 por defecto. Se preserva el servidor/navegador de revisión manual en 5186. No se automatizó esa sesión manual. Advertencia NO_COLOR/FORCE_COLOR en E2E sin fallo (exit 0); PowerShell puede rotular stderr como NativeCommandError.

Nueve nuevas pruebas unitarias cubren pivote/rotación, círculos, inmutabilidad, escala, límites, filtros por contenedor, caras y encuadre. Cinco nuevos componentes más una regresión del flujo cubren selector, estado, teclado/reset, drag/cancelación, leyenda, alta #24, repetir y descartar. Nuevo escenario E2E ejecutado en ambos viewports: drag real de mouse y touch mediante CDP, límites, teclado, alternancia, retazo, métricas, ausencia de overflow y errores JS. Conservados los cuatro escenarios previos.

Capturas auténticas revisadas visualmente, con identificación de piezas y cotas legibles:

| Contenedor | Desktop | Mobile |
|---|---|---|
| Plancha | [3D](desktop-3d.png) | [3D](mobile-3d.png) |
| Retazo/círculo | [3D](desktop-3d-retazo.png) | [3D](mobile-3d-retazo.png) |

Las capturas de progreso, resultado, raster, modal y lista viva se actualizaron al incorporar el selector. Los logs históricos mantienen sus resultados originales. No se ejecutaron backend, PostgreSQL, migraciones ni E2E general que depende de ellos; no se valida integración real ni persistencia. Cobertura HU-015 real y comandos reproducibles permanecen documentados en [compatibility.md](compatibility.md).

## Git y alcance

Comprobaciones iniciales: feature/S1-optimization-ui, HEAD 2d444c0, working tree limpio. Fetch origin --prune correcto, HEAD..origin/integration/sprint-01 vacío; cf84d73 ya estaba incorporado mediante el merge previo 81ce920. No hubo nuevo merge ni conflictos. Cambios limitados a frontend, pruebas/config focal y SPEC/PLAN/TASKS/evidencia. Sin cambios de backend, BD, dependencias o integration; sin rebase ni PR. Commit y push únicamente de la feature, con hashes y resultado comunicados en la entrega final.
