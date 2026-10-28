# SPEC-SP-002 — Reglas comunes FF/BF/WF

Responsable: Andro Quispe. Revisor: Fabricio Melendez Quezada. Fecha: 28/10/2026.
Estado: autorizado por solicitud del usuario; revisión de Fabricio pendiente, sin cierre formal.

## 1. Objetivo
Auditar y consolidar los contratos comunes FF/BF/WF antes de TA-027.
## 2. Alcance
Documentación, pruebas y evidencia; producción solo ante GAP demostrado previamente.
Excluye TA-028/029, merge, rebase, force push y cierre formal.
## 3. Actor y precondiciones
Responsable técnico; integration actualizada y limpia. PR #73 y #75 integrados.
## 4. Entradas y datos
Problema inmutable, grupos por vidrio/espesor, fuentes físicas y configuración raster.
## 5. Reglas de negocio
Preparación, factibilidad, rotación y generación de candidatos comunes. Paso operacional 5°.
FF toma primero; BF minimiza y WF maximiza capacidad libre posterior dentro del nivel permitido.
## 6. Flujo principal
Pedido → preparación → stock compatible → raster → orientaciones → fuentes → candidatos → selector → placement → resultado/métricas.
## 7. Flujos alternativos y errores
Agotamiento y no colocables conservan resultado parcial; errores técnicos no equivalen a NO_FIT.
## 8. Criterios de aceptación
- CA-01: matriz trazable de las 20 reglas solicitadas, con clasificación explícita.
- CA-02: demostrar preparación equivalente, componente de rotación y 5° comunes.
- CA-03: verificar prioridad, compatibilidad, primera orientación/posición, margen y separación.
- CA-04: verificar inmutabilidad, agotamiento, no colocables y reproducibilidad por método.
- CA-05: no exigir patrones iguales; documentar diferencias y GAP antes de cambiar producción.
## 9. Impacto técnico
Optimization: auditoría y tests. API, base de datos y UI: sin cambios previstos.
## 10. Pruebas previstas
Reutilizar suites preparation, stock, rotation, sprint2_angles, retazo_priority, FF/BF/WF,
comparison y slices. Añadir contrato transversal de candidatos y distancias no nulas si falta.
## 11. Evidencias requeridas
`docs/evidence/sprint-02/SP-002/README.md`: base, matriz, arquitectura, pruebas, GAP y conclusión.
## Historial de estado
28/10/2026: SPEC definida; autorización de ejecución del usuario, review pendiente.

28/10/2026: criterios técnicamente verificados; evidencia en `docs/evidence/sprint-02/SP-002/README.md`. Review de Fabricio y cierre formal pendientes.
