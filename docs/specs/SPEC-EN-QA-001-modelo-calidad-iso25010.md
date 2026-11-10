# SPEC-EN-QA-001 — Modelo de calidad ISO/IEC 25010:2023 para NewGlass

## Información general

| Campo | Valor |
|---|---|
| ID | EN-QA-001 |
| Nombre | Modelo de calidad ISO/IEC 25010:2023 para NewGlass |
| Tipo | Enabler (solo documentación, sin código) |
| Sprint | Sprint 2 |
| Prioridad / estimación | Alta / 1 SP |
| Versión | 1.1 |
| Estado | **Implemented**: modelo entregado en este PR; pasa a Verified después de la revisión de Andro (CA-04) y del merge |
| Responsable | Fabricio Danniel Aguilar Chavez (`fabrilar1`) |
| Reviewer | Andro Joseph Quispe Cesias (distinto del autor, CA-04) |
| Rama | `enabler/S2-ENQA001-modelo-calidad-iso25010` |
| Base | `integration-02` en `f46d96d` (después del PR #112) |
| Fecha | 10/11/2026 |
| Tareas relacionadas | TA-QA-001 a TA-QA-010 |
| Entregable | [docs/quality/ISO-25010-modelo-calidad.md](../quality/ISO-25010-modelo-calidad.md) |
| Evidencia | [docs/evidence/sprint-02/EN-QA-001](../evidence/sprint-02/EN-QA-001/README.md) |
| Referencias | [Matriz TA-QA-001](../quality/TA-QA-001-matriz-metricas-iso25023.md) · [SPEC-TA-QA-001](SPEC-TA-QA-001-metricas-calidad-iso25023.md) · [SPEC-TA-QA-003](SPEC-TA-QA-003-adecuacion-funcional.md) · [Convenciones de pruebas](../testing/README.md) |

## 1. Objetivo

Definir el **modelo de calidad de NewGlass** con las nueve características de la
ISO/IEC 25010:2023. Para cada una se indica qué significa en este sistema, qué
módulos afecta, qué riesgos concretos tiene, cómo se evaluará, qué tarea QA del
sprint es responsable y qué evidencia existe hoy en el repositorio.

El modelo es la referencia común para las tareas TA-QA-002 a TA-QA-010 y sirve
para **validar la matriz de métricas de TA-QA-001**, que ya está integrada y declara
que su validación final depende de este modelo.

## 2. Alcance

### Incluye

- Matriz de las nueve características: adecuación funcional, eficiencia de
  desempeño, compatibilidad, capacidad de interacción, fiabilidad, seguridad,
  mantenibilidad, flexibilidad y seguridad operacional (*safety*).
- Definiciones breves **parafraseadas** y subcaracterísticas relevantes.
- Vínculo de cada característica con módulos de NewGlass y riesgos del sistema.
- Forma de evaluación (prueba, medición o revisión) y tarea QA responsable.
- Evidencia existente con ruta, auditada sobre la base indicada.
- Sección de validación de TA-QA-001: cobertura y vacíos, con la tarea que debe
  cubrir cada vacío.
- Prioridades de calidad para NewGlass.
- Nota de alineación entre ISO/IEC 25023:2016 y las ediciones de ISO/IEC 25010.
- Corrección del desfase de L-03 en SPEC-TA-037 (300 → 800 unidades, según
  SPEC-ACADEMIC-800 / PR #108), detectado durante la auditoría (V-17 del modelo).

### Fuera de alcance

- Código, pruebas nuevas, migraciones o cambios de configuración.
- Modificar la matriz de TA-QA-001 (entregable de Andro).
- Ejecutar mediciones o fijar umbrales numéricos: corresponde a cada TA-QA.
- Certificación, auditoría oficial o declaración de conformidad con la norma.
- Actualizar evidencias de otras tareas (S2-WF-CARGA, SPEC-TA-053, SPEC-TA-049);
  solo se registra el desfase y la tarea que lo corrige (V-18 del modelo).
- Cualquier otro cambio en SPEC-TA-037 distinto de la fila L-03 y su historial.

## 3. Situación actual (auditoría F0)

Auditoría de solo lectura sobre `integration-02` en `f46d96d`:

| Hallazgo | Evidencia |
|---|---|
| TA-QA-001 ya está integrada (PR #111) y queda "pendiente de validación final con el modelo de calidad consolidado". | [Matriz TA-QA-001, línea 3](../quality/TA-QA-001-matriz-metricas-iso25023.md) |
| La matriz no tiene métricas de seguridad ("Seguridad de la información no está evaluada"). | [Matriz TA-QA-001, línea 7](../quality/TA-QA-001-matriz-metricas-iso25023.md) |
| Fiabilidad solo tiene MP-05, asignada a TA-QA-002. | [Matriz TA-QA-001, fila MP-05](../quality/TA-QA-001-matriz-metricas-iso25023.md) |
| Todas las métricas están en estado DEFINIDA, sin medición. | [Matriz TA-QA-001, línea 9](../quality/TA-QA-001-matriz-metricas-iso25023.md) |
| Los E2E solo usan Chromium (escritorio 1440 px y móvil 390 px). | `frontend/playwright.config.js` |
| No hay auditoría automática de accesibilidad (axe/WCAG). | Sin dependencias ni pruebas que la usen en `frontend/` |
| Prueba de capas solo en authentication, users, clients y orders. | `backend/tests/unit/**/test_layer_dependencies.py` |
| No hay herramienta de cobertura, duplicación ni complejidad. | `backend/requirements*.txt`, `frontend/package.json` |
| SPEC-TA-049 no está en `integration-02`; solo su review. | [S2-TA049-recuperacion-pedidos.md](../reviews/S2-TA049-recuperacion-pedidos.md) |
| S2-WF-CARGA y SPEC-TA-053 describen el respaldo First Fit de M6, eliminado por el PR #108. | [S2-WF-CARGA](../evidence/sprint-02/S2-WF-CARGA/README.md) · [SPEC-ACADEMIC-800](SPEC-ACADEMIC-800-metodos-independientes.md) |

Módulos reales: backend `authentication, users, clients, inventory, orders,
optimization, results, configuration`; frontend agrega `dashboard`.

## 4. Reglas del modelo

- RN-01: Cada una de las nueve características tiene una fila en la matriz con
  definición, subcaracterísticas, módulos, riesgos, evaluación, tarea QA y evidencia.
- RN-02: Las definiciones son paráfrasis propias; no se copia texto de la norma.
- RN-03: Una subcaracterística de la edición 2023 de la que no se tenga certeza
  se marca **"a confirmar"**; no se inventa.
- RN-04: Cada evidencia citada debe existir en la base auditada, con ruta relativa.
- RN-05: Cada riesgo se expresa en términos del sistema (pedidos, planchas,
  retazos, motores, confirmación, roles), no en términos genéricos.
- RN-06: Cada forma de evaluación indica su tipo: **prueba** (automatizada),
  **medición** (dato cuantitativo con protocolo) o **revisión** (inspección
  documental o de código).
- RN-07: Cada vacío detectado indica qué tarea QA debe cubrirlo.
- RN-08: El modelo no declara certificación ni conformidad, ni atribuye a la
  norma metas o umbrales del proyecto.

## 5. Decisiones y preguntas abiertas

### Decisiones

| ID | Decisión | Motivo |
|---|---|---|
| D-01 | El modelo vive en `docs/quality/ISO-25010-modelo-calidad.md`. | Ya existe `docs/quality/` con la matriz de TA-QA-001; se evita una segunda carpeta. |
| D-02 | Se incluyen `results` (backend) y `dashboard` (frontend) además de los módulos del encargo. | Existen en el código y tienen riesgos propios. |
| D-03 | No se edita la matriz de TA-QA-001; su validación va en una sección del modelo. | Es el entregable de otro integrante; se respeta la regla del equipo. |
| D-04 | Trazabilidad de material no es una característica ISO independiente; se relaciona con adecuación funcional y seguridad (rendición de cuentas). | Coherente con la matriz de TA-QA-001. |
| D-05 | Los desfases de evidencia (TA-049, M6) se registran y se asignan a su tarea; no se corrigen aquí. | Fuera del alcance de un enabler documental. |
| D-06 | El desfase de L-03 en SPEC-TA-037 sí se corrige en este PR, con commit propio: solo la fila L-03 y una línea de historial (v1.5). | Decisión del responsable (10/11/2026): el valor ya está integrado por el PR #108 y la SPEC es de su autoría original (saneamiento de Fabricio Melendez). |

### Preguntas abiertas

| ID | Pregunta | Quién decide |
|---|---|---|
| P-01 | Cotejar IDs, nombres y responsables de TA-QA-001 a TA-QA-010 con Notion. | Equipo / Scrum Master |
| P-02 | Quién agrega las métricas faltantes de seguridad y fiabilidad: una versión nueva de la matriz de TA-QA-001 o las propias TA-QA-004 y TA-QA-006. | Andro y Fabricio Aguilar |
| P-03 | Reparto de TA-QA-008 entre Andro (compatibilidad) y Fabricio Aguilar (despliegue reproducible y contratos). | Equipo |

## 6. Diseño técnico

| Archivo | Cambio |
|---|---|
| `docs/specs/SPEC-EN-QA-001-modelo-calidad-iso25010.md` | Nuevo: esta SPEC. |
| `docs/quality/ISO-25010-modelo-calidad.md` | Nuevo: matriz de las nueve características, validación de TA-QA-001, prioridades y nota 25023/25010. |
| `docs/specs/SPEC-TA-037-control-carga-optimizador.md` | Fila L-03 a 800 unidades (referencia a SPEC-ACADEMIC-800 / PR #108) y línea de historial v1.5. |
| `docs/evidence/sprint-02/EN-QA-001/README.md` | Nuevo: evidencia de entrega y verificación de CA-01 a CA-04. |

Sin cambios en `backend/`, `frontend/`, migraciones ni workflows.

## 7. Criterios de aceptación

| ID | Criterio | Cómo se verifica |
|---|---|---|
| CA-01 | Matriz de las nueve características con definiciones. | Revisión: nueve filas, definición parafraseada en cada una. |
| CA-02 | Cada atributo se vincula a módulos y riesgos. | Revisión: columnas de módulos y riesgos completas en las nueve filas. |
| CA-03 | Se identifica cómo se evaluará cada atributo. | Revisión: tipo de evaluación y tarea QA responsable en las nueve filas. |
| CA-04 | SPEC revisada por un integrante distinto del autor. | Solicitud y aprobación de Andro registradas en el PR. |

## 8. Pruebas previstas

No aplica ejecución de pruebas automatizadas: el cambio es solo documental.
Verificaciones previstas:

- `git diff --check` sin errores de espacios.
- Revisión manual de que cada ruta citada en el modelo existe en la base.
- El CI del PR debe quedar en verde (no hay cambios de código).

## 9. Evidencia requerida

- El modelo de calidad y esta SPEC.
- Salida de `git diff --check` y del estado de la rama antes del PR.
- Revisión de Andro registrada en el PR (CA-04).

## Historial de estado

| Fecha | Versión | Estado | Cambio |
|---|---|---|---|
| 10/11/2026 | 1.0 | Draft | Creación con la auditoría F0, reglas, decisiones y criterios de aceptación. |
| 10/11/2026 | 1.1 | Implemented | Modelo de calidad entregado (CA-01 a CA-03). Corrección de L-03 en SPEC-TA-037 (D-06). Evidencia agregada. Pendiente: revisión de Andro (CA-04) y merge para Verified. |
