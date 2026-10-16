# Auditoría previa a integración — 16/10/2026

SPEC **Reviewed**; PLAN **Approved**. Esta evidencia no cambia sus estados.

| Referencia remota inicial | HEAD observado | Resultado |
|---|---|---|
| integration/sprint-01 | c4c5e5cf046a27cc57e9b33a9bd8f8f144b28f8c | Merge de RBAC; no avances posteriores antes de integrar core. |
| feature/S1-optimization-core | 0e9257249e640614c37799bb4bbb38e75f6033a1 | Coincide con el HEAD solicitado. |
| feature/S1-optimization-ui | 4a3c9c1cd244780f8a1d97f1a527cd1fdebcf760 | UI independiente, con adaptación T1 y RBAC previos. |
| feature/S1-orders-material-flow | 5641bc6aeca0446bc070fc2a2fbc7be58a2f5404 | Editor/payload/materiales; solo observación. |
| feature/S1-dynamic-rbac | 418919337ae74bda7f06bc04d90f065d819fdd0b | Ya incluido mediante c4c5e5c. |
| feature/HU-008-stock-compatible | a0a2dd2 | Antecedente histórico; no se integra. |

No existe otra rama remota activa de Inventory en el listado obtenido. No se
incorporaron reglas de HU-008, cambios de Orders ni commits ajenos por cherry-pick.

## Git

Se ejecutaron `git fetch origin --prune`, status, ramas y logs antes de modificar.
El working tree inicial estaba limpio en core, HEAD local/remoto `0e92572`.
El refspec local inicial era limitado; además se consultaron todas las ramas con:

```bash
git fetch origin '+refs/heads/*:refs/remotes/origin/*' --prune
```

`git merge-base --is-ancestor` confirma que `ebd1bf8`, `691cdd5`, `20f9238`,
`bfdeb74`, `3aca3c8` y `f4dd5a5` siguen presentes en core.

1. Merge normal `--no-ff` core→integration:
   `fe79530ffcd01241fed298a312571a29930c35c8`.
   Padres `c4c5e5c` y `0e92572`; ningún conflicto.
   El árbol resultante coincide exactamente con core. Publicado tras 1976 pruebas.
2. Merge normal `--no-ff` integration→UI:
   `dd35bc32b89339a20a196810e2d0c3af446dcbfc`.
   Padres `4a3c9c1` y `fe79530`; ningún conflicto ni descarte de tests/funcionalidad.

No se hizo merge UI→integration, PR, rebase, squash, reset, force-push ni cambios
en main. Los commits de implementación de UI se crean sobre `dd35bc3`.

## Alembic

```text
... → ta036a1b2c3d
      → s1rbac01a2b3     [head de integration antes del merge]
        → s1opt02b4c6d   [única head del core y del resultado integrado]
```

La revisión multipedido ya existente tiene
`down_revision = s1rbac01a2b3`. Se auditó el grafo en ambas referencias y se
ejecutó `alembic heads` después de integrar. No se crea ninguna migración.
Las pruebas completas incluyen upgrade/downgrade, asociación, backfill,
constraints y atomicidad en PostgreSQL local. Cada `E2E*-runtime.json` registra
la versión real y `alembic_version` del servidor utilizado.

## Orders, Inventory y RBAC

El diff de Orders desde su merge-base contiene siete archivos: formulario,
editor/estilos, listado, repositorio y SPEC propia. No introduce migraciones.
La base compartida ya tiene tipo y espesor por pieza; sus schemas admiten el
payload plano que envía el formulario actual. No se modifica funcionalidad Orders.

Se reejecutó el guardado real desde UI: los seis escenarios HU-007 de integración
y cuatro HU-012 pasan en los dos viewports. No se reproduce el antiguo 422 de
guardado. Esto no atribuye una corrección a un commit no identificado ni usa
el baseline antiguo como resultado actual. Los 422 intencionales de cliente
inexistente y límites raster siguen siendo validaciones esperadas.

RBAC se conserva: `.view` permite consulta, `.execute` inicio y `.confirm`
confirmación. Las autorizaciones reales consultan la BD. Los usuarios E2E tienen
roles sintéticos con capabilities distintas; la aplicación no incorpora una
matriz por nombres de roles.

No cambia ningún archivo de `backend/app` ni de `backend/alembic` respecto de
integration tras incorporar core. Los únicos cambios backend posteriores son
datos/servidor de pruebas locales. Inventory ya representaba
`CONSUMO_OPTIMIZACION`; se verifica su visualización real sin cambiar su lógica.

## Límites conservados

- El algoritmo, geometría, locking, concurrencia, consumo, movimientos y
  confirmación del core permanecen intactos.
- T1 conserva schemas, fixture backend, nombres, Decimal y semántica.
- T1 de corridas entrega contornos orientados y resolución, sin máscaras RLE.
  La UI conserva su inspector y muestra su indisponibilidad cuando faltan máscaras;
  HU-015 conserva raster real en su pestaña, con sus precondiciones originales.
  No se inventa un endpoint ni se rasteriza en frontend.
- La reconciliación administrativa y el mínimo independiente de área residual
  continúan pendientes. No se añade una política ni se alteran estados por UI.
- SPEC Reviewed y PLAN Approved; revisión humana e integración final UI pendientes.
