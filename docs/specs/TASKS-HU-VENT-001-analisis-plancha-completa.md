# TASKS-HU-VENT-001 — Desglose de Tareas de Análisis de Plancha Completa

| Tarea | Descripción | Responsable | Estado |
|---|---|---|---|
| **T01** | Creación de rama `docs/HU-VENT-001-analisis-plancha-completa`, push inicial y formalización SDD (`SPEC`, `TASKS`) | Luis Anthony Ibañez Herrera | [x] Completado |
| **T02** | Auditoría de esquema PostgreSQL (`models.py`), permisos RBAC y stock real en Supabase | Luis Anthony Ibañez Herrera | [x] Completado |
| **T03** | Redacción del Documento de Análisis Comercial y Técnico en `docs/evidence/sprint-02/HU-VENT-001/README.md` | Luis Anthony Ibañez Herrera | [x] Completado |
| **T04** | Elaboración de recomendación estratégica v2 (Incorporar / Postergar / Descartar) | Luis Anthony Ibañez Herrera | [x] Completado |
| **T05** | Compilación de evidencia visual Word para Notion (`Evidencia_Notion_HU-VENT-001.docx`) y cierre SDD en GitHub | Luis Anthony Ibañez Herrera | [x] Completado |

---

## Detalle y Checklist de Criterios

### T01 — Inicio y Especificación Formal SDD
- [x] Crear rama `docs/HU-VENT-001-analisis-plancha-completa` desde `integration-02` y publicar inmediatamente en `origin`.
- [x] Redactar `SPEC-HU-VENT-001-analisis-plancha-completa.md` delimitando que es solo análisis v2 (cero código de ventas).
- [x] Redactar `TASKS-HU-VENT-001-analisis-plancha-completa.md`.

### T02 — Auditoría Técnica sobre Base Real
- [x] Revisar modelos y restricciones `CHECK` en `backend/app/models.py` (`Pedido`, `Pieza`, `Plancha`, `Retazo`, `MovimientoInventario`, `Optimizacion`).
- [x] Revisar catálogo de permisos RBAC en `backend/app/core/permissions.py`.
- [x] Consultar stock real activo en Supabase Cloud (`6` lotes de planchas, `6` retazos activos).

### T03 y T04 — Documento de Análisis Comercial y Recomendación
- [x] Contrastar diferencias operativas, geométricas y económicas entre venta por piezas cortadas vs. plancha completa.
- [x] Documentar análisis de propiedad y ciclo de vida de sobrantes/merma en cada modalidad.
- [x] Mapear cambios requeridos en **Pedidos**, **Inventario**, **Optimización** y **RBAC** si se decidiera implementar en v2.
- [x] Formular veredicto fundamentado (**Postergar a v2 desacoplada** / criterios de decisión).

### T05 — Documentación Visual Notion y Cierre en Git
- [x] Generar capturas visuales en `Notion/HU-VENT-001/img/` y compilar `Evidencia_Notion_HU-VENT-001.docx`.
- [x] Actualizar estado SDD a `Verified` y completar commits y pushes incrementales.
