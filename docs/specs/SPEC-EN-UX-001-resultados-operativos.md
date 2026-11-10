# SPEC-EN-UX-001 — Resultados operativos de NewGlass (auditoría 2026-11-10)

| Campo | Valor |
|---|---|
| Estado | Draft — primer incremento en PR; pendiente de revisión |
| Responsable de implementación | Fabricio Melendez Quezada |
| Fuente principal | `Auditoria_NewGlass_2026-11-10.pdf` (17 p.) y `Auditoria_Complementaria_NewGlass_2026-11-10.pdf` (23 p.), aportados por el responsable |
| Repositorio de código | [newglass-frontend](https://github.com/melendezzz26/newglass-frontend) |
| PR de implementación | [#2 — EN-UX-001](https://github.com/melendezzz26/newglass-frontend/pull/2) — Draft, **no desplegado** |
| Base frontend | `main@816aeddbbd85afca7a5d3ad50dbf37d464a03030` |
| Dependencia de arquitectura | ADR-001; Clean Architecture backend y React por features; contrato comparison-v1/v2 inalterado |
| Compatibilidad | SPEC-TA-046 RN-07 a RN-10: se preservan medidas originales exactas, pero la nueva auditoría reemplaza su regla anterior de repetir la tabla visible en cada motor por una consulta **única por trabajo**. Requiere revisión antes de integrar |

## 1. Problema comprobado

La auditoría principal (10/11/2026) encontró **B01–B05** (incluidos consulta histórica #85, progreso en cálculo, alias de motores, superposición 3D e idioma `lang=en`) y **F01** (no existe cancelación real). La auditoría complementaria reportó **C01–C03** (máscaras históricas expiradas, vidrio no nombrado en visor anidado, fondo variable con altura) y **U01–U08**, destacando **12 310 px** de una solicitud expandida, **4 592 px** entre resultado y dibujo, **220** pendientes unitarias y **13 columnas** de comparación con 777 px de desplazamiento horizontal. Estas medidas corresponden a los escenarios auditados, no a todos los trabajos.

No clasificar como bugs los resultados parciales, las coincidencias entre heurísticas, ni los estados `En optimización` históricos sin proceso vivo. No lanzar pruebas en producción.

## 2. Decisión y alcance de incremento 1

Se prioriza reducir distancia de inspección sin alterar cálculos, contratos o reglas de negocio.

| Hallazgo | Regla del primer incremento | Estado de código |
|---|---|---|
| U02 / Q11 | Barra de contexto compacta sticky para el trabajo, pedidos, estado, motor y tabs; no fijar la cabecera general | Implementado en rama frontend; CI pendiente |
| U05 / Q08 / Q10 | Consulta única y buscable de piezas y medidas; altura acotada; conservar geometrías y datos exactos | Implementado en rama |
| U01 / Q07 | Agrupar sin colocar por pedido/pieza/motivo con acceso a números de unidad; total invariante | Implementado en rama |
| U04 / Q09 y C02 | Un solo visor principal; fuentes abiertas muestran áreas, vidrio, unidad y colocaciones sin crear segundo visor | Implementado en rama |
| U06 / Q12–Q14 | Comparación de seis filas, métrica operativa, estados y causa de no elegibilidad; exactos mm²/ms en detalle, sin ordenar ni recomendar | Implementado en rama |
| B02 | Durante cálculo, no presentar `0 %` como cobertura definitiva; usar indicación de avance pendiente | Mitigación visual en rama; verificación de sincronización real pendiente |

### Reglas de preservación

- Motor FF, BF, WF, HF, M5 y M6-BS sin modificaciones.
- Comparación v1 de tres motores conserva su tabla y semántica legacy.
- Las reglas `eligible`, `selection_allowed`, `confirmable` siguen controladas por el backend; incompletos no se habilitan artificialmente.
- Una prueba del interfaz no realiza confirmación de stock, cancelación de pedido ni escritura de BD.
- El frontend no define lógica SQL o contratos API nuevos.

## 3. Trabajos posteriores (no incluidos ni declarados corregidos en incremento 1)

| Bloque | Hallazgos | Dependencia |
|---|---|---|
| Selección y ficha 2D/3D | U03, Q04–Q06, B04 | Comprobar identidad pedido + pieza + unidad + fuente; mantener zoom |
| Histórico y estado de lectura | B01, C01, U07, U08, UX03, UX06 | Persistencia/representación del snapshot; diagnóstico de #85 separado |
| Nomenclatura, accesibilidad y fondo | B03, B05, C03, UX07, Q18 | Regresión de idioma y contraste, viewport 1366×768 / 1920×1080 |
| Cancelación real P1 | F01, Q17 | **Contrato backend primero**: endpoint autorizado e idempotente, señales al supervisor, parada verificada, conservar resultados y stock, carreras/reinicio; migración Alembic solo si se justifica |
| Otros textos y asistencia operativa | UX01, UX04, UX05, UX09 | No recomendar solución parcial ni inventar ranking |

El flujo de cancelación **no** se implementa mediante un botón React sin backend. Mantener `Pausar vista` como control únicamente visual.

## 4. Pruebas y criterios de aceptación

- CA-01: conservar la navegación por teclado de las pestañas; la barra sticky no tapa el foco ni otros controles en 1366×768 y 1920×1080.
- CA-02: el patrón principal está después del resumen de métricas, antes de listas técnicas; no hay un segundo patrón en MaterialTrace.
- CA-03: 220 unidades pendientes aparecen en un resumen compacto agrupado; se pueden recuperar las 220 unidades exactas.
- CA-04: medidas originales siguen accesibles y no se repiten siete veces entre motores y comparación.
- CA-05: seis motores se identifican en comparación con estado, cobertura, material, merma, recuperable y razón de elegibilidad. Se ofrecen datos exactos por separado.
- CA-06: resultados completos y parciales, selección pendiente, confirmación, work released, refresh e historial mantienen contratos y seguridad anteriores.
- CA-07: `npm run test:unit`, `npm run test:component`, `npm run lint`, `npm run build` y Playwright E2E (PostgreSQL efímero) deben aprobarse en PR. Fallos críticos detienen el incremento.
- CA-08: las resoluciones exactas deben verificarse con prueba de navegador; no afirmar cobertura de 1366×768 ni 1920×1080 sin ejecutarlas.
- CA-09: ningún cambio en backend, esquema de base de datos, motores, permisos ni frontend desplegado por este PR.

## 5. Tareas pequeñas, por prioridad

1. T01 Barra de contexto (U02/Q11) — frontend.
2. T02 Métricas cerca del patrón; medidas compartidas y búsqueda (U05/Q08/Q10) — frontend.
3. T03 Piezas pendientes agrupadas y visor único (U01/U04/C02) — frontend.
4. T04 Comparación compacta y datos exactos (U06/Q12–Q14/B02) — frontend.
5. T05 Regresión completa de UI, foco, viewports y E2E; evidencia en PR — frontend.
6. T06 Selección/inspector 2D/3D y etiquetas 3D — PR siguiente.
7. T07 Corrección de históricos y bugs restantes — PR siguientes.
8. T08 Cancelación P1: SPEC de contrato y PR backend primero, después PR frontend; no fingir operación — pendiente.

## 6. Estado y trazabilidad

- 2026-11-10: Draft. Se revisaron los PDFs y `newglass-frontend/main`. Incremento 1 iniciado en rama `feature/EN-UX-001-resultados-operativos` y presentado como PR #2 Draft.
- Estado `Reviewed` pendiente de revisor; no se cambian el `main`, GitHub Pages o Heroku por este trabajo.
- Resultados del CI/QA se consignarán en el PR y en una revisión de esta SPEC, **sin afirmar pruebas no ejecutadas**.
