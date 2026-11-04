# TA-043 / B11 — Auditoría final y cierre

## Estado

**B11 COMPLETADO TÉCNICAMENTE / CIERRE CONDICIONADO.**

La implementación y las validaciones de TA-043 están trazadas para revisión
humana. El cierre formal permanece condicionado por:

- **RF-20 / CA-20 / HU-018:** HU-018 no pertenece a la base original de TA-043.
- **Heroku:** no se desplegó ni se certificó compatibilidad por extrapolación
  desde WSL2.
- **Capacidad superior a 12 unidades y 150 unidades:** no acreditada.
- La aprobación formal de SPEC/PLAN queda pendiente de Fabricio.

No se modificaron SPEC, PLAN, producción, migraciones compartidas ni ramas
ajenas. La rama parte de `d85a8d3c4fa2ba1b3f70c401ed947adcfbe2470b` mediante
`integration-02`, y el árbol estaba limpio antes de B11.

## Auditoría de bloques

| Bloque | Estado | Evidencia principal |
|---|---|---|
| B01 | CUMPLIDO en su alcance | [B01](../B01/README.md) |
| B02 | CUMPLIDO en su alcance | [B02](../B02/README.md) |
| B03 | CUMPLIDO en su alcance | [B03](../B03/README.md) |
| B04 | CUMPLIDO en su alcance | [B04](../B04/README.md) |
| B05 | CUMPLIDO en su alcance | [B05](../B05/README.md) |
| B06 | CUMPLIDO en su alcance | [B06](../B06/README.md) |
| B07 | CUMPLIDO en su alcance | [B07](../B07/README.md) |
| B08 | CUMPLIDO en su alcance | [B08](../B08/README.md) |
| B09 | CUMPLIDO en su alcance | [B09](../B09/README.md) |
| B10 | CUMPLIDO para 3 y 12 unidades | [B10](../B10/README.md) |
| B11 | CUMPLIDO técnicamente | Este informe y documentos enlazados |

## Verificación integral y regresión

La evidencia B09 registra ST-INT **4/4 PASS** en Chromium escritorio y móvil,
con PostgreSQL aislado, FastAPI, Vite y motores productivos. Incluye
selección, confirmación, idempotencia, recuperación, comparación v1, `/runs`,
visualización 2D/3D y limpieza.

Se conserva el primer intento **3/4**: B08 escritorio falló en la interacción
`radio.check()` sin cambio de estado. B08 aislado pasó y el reintento integral
4/4 pasó; el antecedente se clasifica como fragilidad transitoria de E2E, no
como defecto funcional confirmado ni como estabilidad estadística.

No se suman conteos históricos repetidos. Los resultados acreditados son los
que figuran en las evidencias B01–B10 y sus validadores.

## Garantías críticas

| Garantía | Evidencia |
|---|---|
| Entrada congelada y hash común para seis motores | [B09 smoke](../B09/smoke/), [B10 measurements](../B10/measurements.json) |
| Simulación sin consumo | [B08](../B08/README.md), [B09 validation](../B09/validation.json), [B10](../B10/README.md) |
| Selección exclusivamente manual | [B08](../B08/README.md), [B09 smoke](../B09/smoke/) |
| Solo resultado completo/elegible confirmable | [B08](../B08/README.md), contrato [comparison-v2](../../../../contracts/optimization/comparison-v2.md) |
| Consumo exclusivo y transacción atómica | [B08](../B08/README.md), recibos y movimientos en [B09 smoke](../B09/smoke/) |
| Idempotencia, conflictos y rollback | [B08](../B08/README.md), [B09](../B09/README.md) |
| Compatibilidad v1 y `/runs` | [B06](../B06/README.md), `TA-043-b07-history-v1-legacy.json` |
| Admisión posterior al cierre seguro | [B04](../B04/README.md), [B05](../B05/README.md), [B10](../B10/README.md) |
| Recuperación ambigua conserva bloqueo | [B05](../B05/README.md), [B06](../B06/README.md) |
| Propiedad de máscaras y snapshots | [B01](../B01/README.md), [B03](../B03/README.md), [B09](../B09/README.md) |

## Capacidad y operación

B10 midió dos casos con los seis motores reales:

- 3 unidades: 6/6 completos, 2.652 s, RSS máximo 61.3 MiB.
- 12 unidades: 6/6 completos, 2.978 s, RSS máximo 61.9 MiB.

Se respetaron un worker, 180 s globales, 120 s por motor, RSS/VM/IPC y
retención originales. No se acredita 150 unidades, cargas grandes generales,
Heroku ni una instancia web múltiple. La operación depende de `procfs`,
`prctl`, `RLIMIT_AS`, `spawn` y cierre de descendientes en Linux. Una
recuperación ambigua puede requerir intervención operativa controlada.

## Revisión Git e integración

- Base: `integration-02` = `d85a8d3c4fa2ba1b3f70c401ed947adcfbe2470b`.
- Último código/evidencia B10: `05ab9cb`.
- Los PR #96–#100 no fueron incorporados.
- No se hizo push, merge, rebase, deploy ni migración compartida.
- El validador reproducible es [optimization_b11_validation.py](../../../../../backend/tests/optimization_b11_validation.py).
- La matriz completa está en [traceability.md](./traceability.md).
- Los riesgos están en [risks.md](./risks.md).
- El inventario de evidencias está en [evidence-index.md](./evidence-index.md).
- El checklist de integración está en [integration-checklist.md](./integration-checklist.md).
- La descripción propuesta de PR está en [pr-description.md](./pr-description.md).

## Recomendación

Preparar un PR local hacia `integration-02` después de revisión humana de esta
matriz. No abrirlo ni hacer push todavía. Antes de desplegar deben resolverse
la decisión sobre HU-018, la compatibilidad real de la plataforma Linux
objetivo/Heroku, la capacidad requerida por encima de 12 unidades y la
política operativa para recuperaciones ambiguas.
