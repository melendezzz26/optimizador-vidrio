# PLAN-TA-QA-005 — Plan de Evaluación de Usabilidad y Accesibilidad

## 1. Objetivo y Estrategia

El presente plan establece la metodología técnica para auditar y cuantificar la usabilidad, navegación por teclado, accesibilidad WCAG y responsividad móvil de NewGlass, cumpliendo con el mandato explícito: **ejecución 100% sobre conexiones reales a la base de datos y al backend, sin el uso de APIs simuladas ni mocks**.

La estrategia se fundamenta en:
1. **Conexiones Reales de Extremo a Extremo:** El backend FastAPI (`backend/main.py`) opera con su conexión real a PostgreSQL en Supabase, garantizando que cada consulta, creación de pedidos, filtrado de inventario y optimización refleje el comportamiento real de producción.
2. **Pruebas Automatizadas de Interacción con Playwright:** Scripts E2E que simulan el comportamiento del usuario mediante eventos de teclado reales (`page.keyboard.press`), verificando foco, áreas táctiles y tiempos de respuesta.
3. **Métricas Cuantitativas Estandarizadas:**
   - **Tiempo de Tarea ($T$):** Duración en segundos desde el inicio de la acción hasta la confirmación visual.
   - **Completitud ($C\%$):** Porcentaje de tareas finalizadas sin bloqueo.
   - **Tasa de Errores ($E$):** Incidencias o validaciones fallidas registradas durante el flujo.
4. **Auditoría de Accesibilidad (WCAG 2.1 AA) y Móvil:** Inspección de foco, semántica ARIA, trampas de foco en diálogos modales y verificación de desbordamiento horizontal en pantallas de $375\text{ px}$.

---

## 2. Arquitectura de Prueba con Conexiones Reales

```text
┌─────────────────────────────────────────────────────────────┐
│                       PLAYWRIGHT E2E                        │
│            (Navegación real por teclado, eventos,            │
│             foco y viewport móvil a 375x667)                │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP / WebSocket
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND VITE / REACT                    │
│           (React 19, componentes reales de UI,               │
│            FormularioPedido, InventoryPage, Optimization)   │
└──────────────────────────────┬──────────────────────────────┘
                               │ REST API (JSON)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    BACKEND FASTAPI REAL                     │
│               (backend/main.py en puerto 8000)              │
└──────────────────────────────┬──────────────────────────────┘
                               │ TCP / Pooler (5432)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│               POSTGRESQL REAL (SUPABASE CLOUD)              │
│       (aws-0-us-east-1.pooler.supabase.com:5432/postgres)   │
│       Tablas reales: usuarios, clientes, planchas, pedidos  │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Matriz de Riesgos y Mitigación

| Riesgo Técnico | Impacto | Mitigación |
|---|---|---|
| **Contaminación de datos en BD real** | Creación descontrolada de registros de prueba. | Los flujos de prueba usan identificadores claramente etiquetados como `TEST-QA-005` y se limpian o aíslan tras la prueba. |
| **Latencia de red con Supabase** | Variabilidad en los tiempos medidos. | Se mide por separado el tiempo de interacción en UI (foco/teclado) del tiempo de respuesta de red del backend. |
| **Falsos positivos de foco por mouse** | Simulación de teclado que oculta problemas reales. | El arnés deshabilita clics con mouse en los flujos de teclado; únicamente interactúa con `Tab`, `Enter`, flechas y `Escape`. |

---

## 4. Fases de Ejecución

1. **Fase 1 — Especificación SDD y Documentación Inicial (`T01`):** Redacción de `SPEC`, `PLAN`, `TASKS` y commit inicial.
2. **Fase 2 — Suite de Pruebas E2E sobre Backend Real (`T02`):** Implementar la suite `qa005-usability.spec.js` cubriendo las 8 tareas de usuario en Pedidos, Inventario y Optimización.
3. **Fase 3 — Ejecución y Medición Cuantitativa (`T03`):** Registrar tiempos, errores y porcentaje de éxito con el backend y base de datos activos.
4. **Fase 4 — Auditoría de Accesibilidad y Responsividad Móvil (`T04`):** Evaluar contención de foco, navegación por teclado en modales y viewport móvil de 375 px.
5. **Fase 5 — Matriz de Problemas y Propuestas de Mejora (`T05`):** Clasificar hallazgos por severidad e impacto UX.
6. **Fase 6 — Evidencia Formal, Word para Notion y Cierre SDD (`T06`):** Documentar en `docs/evidence/sprint-02/TA-QA-005/README.md`, actualizar el Word de Notion y realizar commit/push final.
