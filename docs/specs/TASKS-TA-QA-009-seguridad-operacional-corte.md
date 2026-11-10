# TASKS-TA-QA-009 — Desglose de Tareas de Seguridad Operacional del Corte

| Tarea | Descripción | Responsable | Estado |
|---|---|---|---|
| **T01** | Setup de rama Git (`qa/TA-QA-009-...`), push inicial y formalización SDD (`SPEC`, `PLAN`, `TASKS`) | Luis Anthony Ibañez Herrera | [x] Completado |
| **T02** | Elaboración formal de la Matriz de Riesgos Operacionales y Medidas Preventivas | Luis Anthony Ibañez Herrera | [x] Completado |
| **T03** | Implementación del arnés automatizado de pruebas para patrones inválidos sobre conexiones reales | Luis Anthony Ibañez Herrera | [x] Completado |
| **T04** | Ejecución de batería `CP-SEC-01` a `CP-SEC-08` contra backend real + Supabase y verificación de rechazo 100% | Luis Anthony Ibañez Herrera | [x] Completado |
| **T05** | Documentación de evidencias en Word para Notion (`Evidencia_Notion_TA-QA-009.docx`) | Luis Anthony Ibañez Herrera | [x] Completado |
| **T06** | Emisión de reporte final (`docs/evidence/sprint-02/TA-QA-009/README.md`) y cierre SDD en GitHub | Luis Anthony Ibañez Herrera | [x] Completado |

---

## Detalle y Checklist Operacional

### T01 — Inicio y Especificación Formal SDD
- [x] Crear rama `qa/TA-QA-009-seguridad-operacional-corte` y hacer push inmediato a `origin`.
- [x] Redactar `SPEC-TA-QA-009-seguridad-operacional-corte.md` definiendo `RN-SEC-01` a `RN-SEC-08` y `CP-SEC-01` a `CP-SEC-08`.
- [x] Redactar `PLAN-TA-QA-009-seguridad-operacional-corte.md`.
- [x] Redactar `TASKS-TA-QA-009-seguridad-operacional-corte.md`.

### T02 — Matriz de Riesgos Operacionales
- [x] Documentar riesgos industriales en taller (corte al vacío, fractura explosiva por tensión, colisión de diamante, astillamiento por puente insuficiente).
- [x] Asignar severidad, probabilidad y nivel de riesgo según matriz 4×4.
- [x] Mapear cada riesgo con su barrera lógica en software y medida preventiva física (EPP / protocolo de quiebre).

### T03 — Arnés Automatizado de Seguridad
- [x] Construir `backend/scripts/test_ta_qa_009_safety.py` conectado al backend real (`main.app`) y Supabase PostgreSQL.
- [x] Implementar los 8 casos de inyección de fallos y patrones inválidos (`CP-SEC-01` a `CP-SEC-08`).

### T04 — Ejecución y Verificación de Rechazo
- [x] Ejecutar las pruebas y comprobar que el **100%** de los patrones inválidos son bloqueados (`SUPERPOSICION`, `MARGEN_INSUFICIENTE`, `SEPARACION_INSUFICIENTE`, `FUERA_DE_LIMITE`, `HTTP 422`, `NOT_CONFIRMABLE`).
- [x] Guardar trazas y capturas visuales de cada rechazo.

### T05 y T06 — Documentación Notion y Cierre en GitHub
- [x] Generar y compilar el documento Word completo con subtítulos y capturas (`Evidencia_Notion_TA-QA-009.docx`).
- [x] Publicar reporte de evidencia en `docs/evidence/sprint-02/TA-QA-009/README.md`.
- [x] Actualizar estado a `Verified` y ejecutar commits + pushes incrementales hasta cerrar la rama.
