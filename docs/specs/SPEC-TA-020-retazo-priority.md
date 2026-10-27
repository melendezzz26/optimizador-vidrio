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

Fuente: aclaración del usuario del 27/10/2026 con la información disponible del
backlog TA-020 / T01. Objetivo / descripción: «Aplicar una política uniforme de
evaluación de retazos compatibles antes de planchas nuevas para FF/BF/WF».

Criterios **provisionales** expresamente autorizados por el usuario; se transcribe
su regla funcional. No sustituyen la revisión pendiente de Fabricio.

- CA-01: Evaluar primero retazos compatibles.
- CA-02: Si existe al menos un retazo factible, FF/BF/WF deben resolver únicamente dentro del nivel retazo.
- CA-03: Las planchas nuevas solo se evalúan si no existe ningún retazo factible.
- CA-04: Material con tipo de vidrio o espesor incompatible nunca debe ofrecerse como candidato.
- CA-05: La regla debe ser reproducible y determinista.
- CA-06: Simular no debe modificar inventario.

Se mantienen los seis escenarios originales: retazo y plancha factibles,
retazo no factible, sin retazo, incompatibilidad, determinismo y simulación.
Los CA-01 a CA-03 se alinean ahora con los puntos confirmados por el usuario;
sus números no corresponden a los números de los escenarios originales.

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
- Matriz de los seis CA provisionales confirmados; revisión de Fabricio pendiente, sin declarar cierre.

## Historial de estado

- 27/10/2026 — Draft: SPEC creada antes de pruebas nuevas; revisión Pendiente.
- 27/10/2026 — Draft: incorporados los seis CA provisionales confirmados por el usuario; revisión Pendiente.
