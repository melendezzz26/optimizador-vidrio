# SPEC-SP-002 ? Reglas comunes FF/BF/WF

Responsable: Andro Quispe. Revisor: Fabricio Melendez Quezada. Fecha: 28/10/2026.
Estado: autorizado por solicitud del usuario; revisi?n de Fabricio pendiente, sin cierre formal.

## 1. Objetivo
Auditar y consolidar los contratos comunes FF/BF/WF antes de TA-027.
## 2. Alcance
Documentaci?n, pruebas y evidencia; producci?n solo ante GAP demostrado previamente.
Excluye TA-028/029, merge, rebase, force push y cierre formal.
## 3. Actor y precondiciones
Responsable t?cnico; integration actualizada y limpia. PR #73 y #75 integrados.
## 4. Entradas y datos
Problema inmutable, grupos por vidrio/espesor, fuentes f?sicas y configuraci?n raster.
## 5. Reglas de negocio
Preparaci?n, factibilidad, rotaci?n y generaci?n de candidatos comunes. Paso operacional 5?.
FF toma primero; BF minimiza y WF maximiza capacidad libre posterior dentro del nivel permitido.
## 6. Flujo principal
Pedido ? preparaci?n ? stock compatible ? raster ? orientaciones ? fuentes ? candidatos ? selector ? placement ? resultado/m?tricas.
## 7. Flujos alternativos y errores
Agotamiento y no colocables conservan resultado parcial; errores t?cnicos no equivalen a NO_FIT.
## 8. Criterios de aceptaci?n
- CA-01: matriz trazable de las 20 reglas solicitadas, con clasificaci?n expl?cita.
- CA-02: demostrar preparaci?n equivalente, componente de rotaci?n y 5? comunes.
- CA-03: verificar prioridad, compatibilidad, primera orientaci?n/posici?n, margen y separaci?n.
- CA-04: verificar inmutabilidad, agotamiento, no colocables y reproducibilidad por m?todo.
- CA-05: no exigir patrones iguales; documentar diferencias y GAP antes de cambiar producci?n.
## 9. Impacto t?cnico
Optimization: auditor?a y tests. API, base de datos y UI: sin cambios previstos.
## 10. Pruebas previstas
Reutilizar suites preparation, stock, rotation, sprint2_angles, retazo_priority, FF/BF/WF,
comparison y slices. A?adir contrato transversal de candidatos y distancias no nulas si falta.
## 11. Evidencias requeridas
`docs/evidence/sprint-02/SP-002/README.md`: base, matriz, arquitectura, pruebas, GAP y conclusi?n.
## Historial de estado
28/10/2026: SPEC definida; autorizaci?n de ejecuci?n del usuario, review pendiente.
