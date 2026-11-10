# TASKS-TA-QA-005 — Desglose de Tareas de Usabilidad y Accesibilidad

| Tarea | Descripción | Responsable | Estado |
|---|---|---|---|
| **T01** | Redacción de `SPEC-TA-QA-005` y `PLAN-TA-QA-005` con mandato de conexiones reales | Luis Anthony Ibañez Herrera | [x] Completado |
| **T02** | Implementación de suite de pruebas de usabilidad y teclado sobre conexiones reales | Luis Anthony Ibañez Herrera | [x] Completado |
| **T03** | Ejecución de los escenarios de Pedidos, Inventario y Optimización y medición de tiempos/errores | Luis Anthony Ibañez Herrera | [x] Completado |
| **T04** | Auditoría de accesibilidad (WCAG 2.1 AA, navegación por teclado, foco) y prueba móvil a 375 px | Luis Anthony Ibañez Herrera | [x] Completado |
| **T05** | Elaboración de la Matriz de Problemas Encontrados y Propuestas de Mejora | Luis Anthony Ibañez Herrera | [x] Completado |
| **T06** | Generación de evidencia formal, reporte Word para Notion y cierre SDD en Git | Luis Anthony Ibañez Herrera | [x] Completado |

---

## Detalle y Checklist de Criterios

### T01 — Especificación Formal SDD
- [x] Crear y publicar la rama `qa/TA-QA-005-usabilidad-accesibilidad` en GitHub.
- [x] Redactar `SPEC-TA-QA-005` formalizando las 8 tareas y reglas de conexiones reales.
- [x] Redactar `PLAN-TA-QA-005` con arquitectura de prueba y mitigación de riesgos.
- [x] Realizar commit y push incremental de la especificación.

### T02 — Arnés y Suite de Usabilidad Real
- [x] Configurar arnés de prueba Playwright apuntando al backend real en `http://127.0.0.1:8000`.
- [x] Diseñar helpers de interacción exclusiva por teclado (`Tab`, `Shift+Tab`, `Enter`, `Escape`).
- [x] Implementar aserciones de captura de tiempos por tarea y contención de foco.

### T03 — Ejecución de Escenarios Concretos
- [x] Ejecutar flujo de Pedidos (selección de cliente, polígono convexo y guardado).
- [x] Ejecutar flujo de Inventario (filtro de stock, registro de plancha y baja de retazo).
- [x] Ejecutar flujo de Optimización (apertura de orden, comparación 2D/3D y confirmación).
- [x] Medir y tabular tiempos de interacción, tasa de completitud y errores.

### T04 — Accesibilidad y Responsividad Móvil
- [x] Auditar foco en modales (trampa de foco al abrir y retorno de foco al cerrar con Escape).
- [x] Verificar atributos semánticos ARIA (`role="dialog"`, `aria-current`, `aria-label`).
- [x] Comprobar ausencia de desbordamiento horizontal en viewport móvil de 375 px (`scrollWidth <= innerWidth`).
- [x] Verificar áreas táctiles mínimas de 44x44 px en botones de acción.

### T05 — Matriz de Problemas y Mejoras
- [x] Clasificar problemas detectados por severidad (Alta, Media, Baja).
- [x] Proponer soluciones concretas de código/diseño para cada hallazgo.

### T06 — Cierre Documental y Entrega
- [x] Redactar `docs/evidence/sprint-02/TA-QA-005/README.md`.
- [x] Compilar informe final en Word con capturas para Notion (`Evidencia_Notion_TA-QA-005.docx`).
- [x] Actualizar estado de `SPEC-TA-QA-005` a `Verified`.
- [x] Realizar commit final y push a GitHub.
