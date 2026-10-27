# SPEC-TA-020 — Prioridad de retazos

## Información general

| Campo | Valor |
|---|---|
| Estado | Draft |
| PBI relacionado | TA-020 / T01 — Generalizar preferencia retazo → plancha |
| Responsable | Andro Quispe |
| Reviewer | Fabricio Melendez Quezada |
| Periodo | 21/10/2026 – 28/10/2026 |
| Estado de revisión | Pendiente |

## 1. Objetivo

Verificar que FF, BF y WF aplican una política común y determinista: un retazo
compatible y factible tiene prioridad absoluta sobre cualquier plancha.

## 2. Alcance

### Incluye

- Auditoría de stock, candidatos y selección; pruebas comunes y evidencia.
- Reutilizar la implementación si satisface la regla, sin cambios artificiales.

### Fuera de alcance

- Cambios en packing.py, first_fit.py, best_fit.py y worst_fit.py.
- Comparación multimétodo, TA-021/TA-025, UI, migraciones y consumo de inventario.
- PR, merge, rebase y cierre de TA-020.

## 3. Actor y precondiciones

**Actor:** responsable técnico y revisor del Sprint 2.

**Precondiciones:**

- Problema válido agrupado por tipo de vidrio y espesor; stock disponible.
- Base integration actualizada; revisión humana pendiente, sin atribuir aprobación.

## 4. Entradas y datos

| Campo / dato | Tipo / formato | Regla |
|---|---|---|
| Material | tipo de vidrio, espesor decimal | Coincidencia exacta |
| Fuente | RETAZO / PLANCHA | Dos niveles separados |
| Geometría y configuración | Contratos actuales | Factibilidad raster real |
| Unidades | Piezas y fuentes físicas | Recalcular factibilidad tras cada placement |

## 5. Reglas de negocio

- RN-01: buscar retazos compatibles y factibles antes de evaluar planchas.
- RN-02: FF/BF/WF seleccionan exclusivamente dentro del primer nivel factible.
- RN-03: excluir material incompatible antes de seleccionar.
- RN-04: misma entrada produce misma fuente y placement; optimizar no consume stock.

## 6. Flujo principal

1. Filtrar y validar stock compatible.
2. Buscar candidatos factibles del nivel retazo para cada unidad.
3. Resolver FF/BF/WF dentro del nivel; aplicar el ganador al layout local.
4. Evaluar planchas solamente si no hay ganador retazo.

## 7. Flujos alternativos y errores

- Sin retazos o con retazos no factibles: intentar planchas.
- Sin fuente factible: conservar unidad no colocada, según contrato vigente.
- Proveedor incompatible o grupo inválido: rechazar antes del selector.

## 8. Criterios de aceptación

La transcripción literal del CA del backlog está pendiente: no se encontró
TA-020 en archivos versionados ni mediante búsqueda de Notion. Se solicitó
la referencia al usuario. Los siguientes son criterios operativos derivados
de su instrucción, **no una cita del backlog**:

- CA-01: retazo factible + plancha factible → retazo en FF/BF/WF; plancha no evaluada.
- CA-02: retazo compatible no factible → plancha en FF/BF/WF.
- CA-03: sin retazo → plancha en FF/BF/WF.
- CA-04: otro vidrio u otro espesor nunca llega como candidato al selector.
- CA-05: misma entrada → mismo nivel, fuente y placement.
- CA-06: evaluación/simulación no modifica inventario.

## 9. Impacto técnico

### Módulos

- Optimization: inspección de dominio/aplicación/adaptador, pruebas únicamente.

### API

- Sin cambios.

### Base de datos / migración

- Sin cambios; verificación con SQLite local de pruebas.

### UI

- Sin cambios.

## 10. Pruebas previstas

- Reutilizar regresiones FF/BF/WF, stock y slices de repositorios reales.
- Añadir matriz parametrizada de seis casos y agotamiento por unidad.
- Espiar rasterización para comprobar que no se evalúan planchas prematuramente.

## 11. Evidencias requeridas

- `docs/evidence/sprint-02/TA-020/`: base, auditoría, clasificación, resultados,
  matriz CA → pruebas y diff sin producción.
- Literal del backlog y revisión de Fabricio pendientes; no declarar cierre.

## Historial de estado

- 27/10/2026 — Draft: SPEC creada antes de pruebas nuevas; revisión Pendiente.
