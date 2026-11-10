# ADR-003 — Separación física de repositorios de frontend y backend

- **Estado:** Accepted
- **Fecha:** 2026-11-10
- **PBI:** [EN-REPO-001 — Notion](https://app.notion.com/p/414e0c471a44812297f7ee150e15781b)
- **SPEC:** [SPEC-EN-REPO-001](../specs/SPEC-EN-REPO-001-separacion-repositorios.md)
- **PLAN:** [PLAN-EN-REPO-001](../specs/PLAN-EN-REPO-001-separacion-repositorios.md)
- **Relacionados:** [ADR-001](ADR-001-seleccion-arquitectura.md), ADR-002, TA-DEPLOY-001

## Contexto

La arquitectura NewGlass aceptada en ADR-001 define React/Vite, FastAPI monolítico modular con Clean Architecture, PostgreSQL/Supabase y comunicación HTTP. El producto comenzó como monorepo `optimizador-vidrio`, con `frontend/`, `backend/`, documentación, experimentos y Actions compartidos.

Por instrucción del ingeniero, el equipo debe organizar el **frontend y backend en repositorios GitHub distintos**, sin cambiar la arquitectura funcional, los seis motores, los modelos de dominio ni las operaciones transaccionales. La plataforma ya despliega Pages y Heroku separadamente: lo nuevo es la **frontera del control de versiones, revisiones y CI**, no un diseño de microservicios.

La línea base documental observada en GitHub es `integration-02@f46d96db9f5ca6071445bae5f884908aed734ff4` el 2026-11-10. Ese valor no se congela como corte definitivo hasta revisar PR abiertos y aprobarlo.

## Decisión aceptada

1. Adoptar dos repositorios GitHub independientes: uno de frontend React/Vite y otro de backend FastAPI, conservando una API HTTP/HTTPS explícita como frontera.
2. Preservar backend como **un solo despliegue lógico de monolito modular**, con sus reglas Clean Architecture y acceso exclusivo a PostgreSQL/Supabase. El frontend permanece SPA organizada por features.
3. Mantener desarrollo trazable por PBI → SPEC → implementación → pruebas → evidencia → PR, con ramas y protecciones por repositorio.
4. Filtrar el historial Git de cada subdirectorio desde un SHA integrado aprobado, conservar metadatos de autoría y producir correspondencia de commits con sus SHA originales. Preservar monorepo como histórico de consulta.
5. Designar contrato API versionado como interfaz explícita entre repos; requerir matriz de compatibilidad entre SHA frontend/backend y gate E2E con checkouts definidos.
6. Ubicar CI backend y frontend en sus repos; coordinar E2E entre ambos sin depender de rutas relativas de un monorepo. Staging debe continuar sin credenciales en los jobs de PR.
7. Trasladar origen de Heroku y publicación Pages **solo después** de pruebas, revisión y autorización humana de cutover. Mantener rollback independiente de apps.
8. Mantener sin cambios el presupuesto y la lógica de comparación de seis motores, la supervisión de procesos, la semántica de auth/JWT, la API y Alembic.

## Alternativas consideradas

### Seguir como monorepo con pipelines separados

Técnicamente viable y arquitectura lógica conservada, pero **no cumple la instrucción explícita del ingeniero** de separar repositorios.

### Copiar `frontend/` y `backend/` como repositorios nuevos con un único commit

Implementación inicial simple, pero pierde trazabilidad directa de la contribución histórica y dificulta auditoría académica de commits. No es la estrategia preferida.

### Dos repositorios con historial filtrado

**Propuesta seleccionada.** Requiere herramientas de filtrado, mapeo de commits y adaptación de pruebas transversales, pero conserva atribución y evolución verificables.

### Migrar a microservicios/duplicar base de datos

Descartado: no se necesita para la separación de repositorios y agrega riesgos de coordinación, operación y consistencia.

## Consecuencias

**Positivas:** ownership y permisos más claros; CI/despliegues autónomos; fronteras frontend/API explícitas; trazabilidad de cambios propia para cada equipo.

**Costos y riesgos:** commits nuevos con hashes distintos tras filtrado; PR/issues/tags/protecciones no viajan automáticamente; dependencias `../backend`, workflows compartidos y documentos transversales requieren adaptación; riesgos temporales de incompatibilidad de versiones y dos publicaciones Pages.

## Decisiones operativas pendientes antes del corte

- Nombres y visibilidad de ambos repos, miembros/roles y rama de integración de cada uno.
- SHA de corte, política para PR #113/#114 u otros PR pendientes y respaldo verificable.
- Ubicación y autoridad del contrato API, evidencia histórica y runners E2E.
- Estrategia Pages (cambio de URL o dominio) y cutover/rollback Heroku.
- Asignar responsable y revisor de la implementación.

## Compatibilidad con ADR-001

Este ADR **complementa** ADR-001 cambiando únicamente la organización física de los repositorios y la gobernanza del CI/CD. No sustituye sus decisiones sobre cliente-servidor de tres niveles, Clean Architecture, módulos, base de datos, dominio ni contrato entre componentes.

## Estado

2026-11-10: Accepted por aprobación expresa del responsable del proyecto. Se autoriza preparar la implementación y las extracciones reproducibles; la aprobación de ADR no autoriza cambios de despliegue ni migraciones de datos sin los gates del PLAN.
