# Descripción propuesta de PR — TA-043 → `integration-02`

## Objetivo

Integrar la comparación v2 de seis motores de corte de vidrio, manteniendo
compatibilidad con comparison-v1 y `/runs`, con selección manual y
confirmación transaccional segura.

## Alcance

Incluye FF, BF, WF, HF, M5 y M6-BS; contratos versionados, persistencia,
adaptadores, supervisor secuencial, API v2, recuperación, workspace frontend,
selección, confirmación, regresiones y evidencias B01–B11.

## Validación

- Regresiones backend/frontend y lint/build documentados en B09.
- ST-INT real 4/4 en escritorio y móvil con PostgreSQL aislado, FastAPI, Vite
  y Chromium.
- Idempotencia, conflictos, rollback, v1, `/runs` y limpieza documentados.
- B10: seis motores completos en cargas de 3 y 12 unidades, un worker y
  presupuestos originales.

## Riesgos y dependencias

- RF-20/HU-018 es condicionado y no se incorpora en este PR.
- Heroku no está certificado.
- No se acredita capacidad de 150 unidades ni cargas superiores a 12.
- La ejecución depende de mecanismos Linux y de una única instancia/proceso web.
- Los PR #96–#100 apuntan a `integration-01`; no fueron incorporados y pueden
  producir conflictos en pedidos, inventario o interfaz.

## Checklist antes del merge

- [ ] Revisión humana de SPEC/PLAN y matriz B11.
- [ ] Resolver cualquier conflicto con `integration-02` sin alterar contratos v1.
- [ ] Repetir pruebas afectadas por conflictos.
- [ ] Confirmar migraciones y variables de entorno en integración privada.
- [ ] Confirmar ausencia de secretos y archivos temporales.
- [ ] Mantener RF-20 como condicionado.
- [ ] Obtener aprobación explícita antes de merge/push/deploy.

