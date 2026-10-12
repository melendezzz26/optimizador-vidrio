# Seguimiento de seguridad — `source-map-js`

- **Rama:** `feature/TA-DEPLOY-001-staging`
- **Ejecución:** validaciones locales Windows; no se hizo deployment.

## Diagnóstico

`source-map-js` era una dependencia transitiva de desarrollo/build, no directa ni de runtime. El lockfile contenía una sola resolución, compartida por estas cadenas:

- `jsdom@30.1.2 → css-tree@3.2.1 → source-map-js@1.2.1`
- `vite@8.3.1 → postcss@8.5.28 → source-map-js@1.2.1`

`css-tree` y `postcss` solicitan `source-map-js@^1.2.1`; ese rango admite `1.2.2`. El advisory [GHSA-68fv-2mgg-jv7q](https://github.com/advisories/GHSA-68fv-2mgg-jv7q), también identificado como CVE-2026-93749, afecta versiones `<1.2.2`. Describe bloqueo síncrono del event loop al procesar offsets de secciones malformadas en source maps indexados. `1.2.2` es la versión corregida.

## Cambio

- **Antes:** `source-map-js@1.2.1`.
- **Después:** `source-map-js@1.2.2`, deduplicado en ambas cadenas.
- **Mecanismo:** `npm.cmd update source-map-js --ignore-scripts --no-audit --cache "$env:TEMP\ta-deploy-npm-cache"`.
- Solo cambió la resolución e integridad de esa entrada en `package-lock.json`; `package.json` no cambió y no se añadió dependencia directa ni `overrides`.

## Auditorías npm

Resultados antes del cambio:

| Comando | Resultado |
|---|---|
| `npm audit` | 1 vulnerabilidad **HIGH**, `source-map-js` 1.0.0–1.2.1, GHSA-68fv-2mgg-jv7q. |
| `npm audit --omit=dev` | 0 vulnerabilidades. |

Resultados después del cambio:

| Comando | Resultado |
|---|---|
| `npm audit` | 0 vulnerabilidades. |
| `npm audit --omit=dev` | 0 vulnerabilidades. |

La primera consulta desde el entorno restringido no llegó al endpoint de auditoría del registry; se reintentó con acceso al registry y se registran arriba las respuestas exitosas. No se ocultaron advisories.

## Validación frontend

| Comando | Resultado |
|---|---|
| `npm run test:unit` | 101 passed, 0 failed, 0 skipped. |
| `npm run test:component` | 20 archivos passed; 206 tests passed, 0 failed. |
| `npm run lint` | PASS. |
| `npm run build` | PASS; Vite 8.3.1, 1941 módulos transformados. |
| Build Staging con `VITE_API_URL=https://api.example.test` | PASS; Vite 8.3.1, 1941 módulos transformados. URL HTTPS sintética, sin credenciales. |
| `npm run check:staging` | PASS: base Pages y assets presentes; bundle sin localhost, DSN, nombres de secretos ni patrones de tokens privados. |

Inspección adicional de `dist`: API sintética presente; base `/optimizador-vidrio/` presente; `localhost`, `DATABASE_URL`, `SECRET_KEY` y patrones de tokens privados ausentes.

## E2E

La validación E2E manual posterior al cambio se ejecutó con:

- **Python:** `backend/venv/Scripts/python.exe`, localizado primero.
- **Versión:** Python 3.11.9.
- **Comando:** `npm run test:e2e`.
- **Resultado:** 32 casos descubiertos; 31 passed, 1 skipped, 0 failed.
- **Duración:** 34.8 s.

El único skip corresponde a “HU-014 Almacenero registra una baja” en
chromium-mobile. El escenario equivalente desktop pasó y el caso de permisos
HU-014 pasó. La imposibilidad anterior de ejecutar E2E correspondía al entorno
de Codex y queda reemplazada por esta ejecución manual válida; no constituye un
bloqueo vigente.

## Estado del preflight

Resultados registrados después de corregir la dependencia:

- `source-map-js`: anterior `1.2.1`, actual `1.2.2`.
- `npm audit`: 0 vulnerabilities.
- `npm audit --omit=dev`: 0 vulnerabilities.
- Frontend unit: 101 passed.
- Frontend component: 206 passed.
- Lint: PASS.
- Build: PASS.
- Build Staging / check Staging: PASS.
- E2E: 31 passed, 1 skipped, 0 failed (32 descubiertos; 34.8 s).

La recomendación es **READY FOR HUMAN STAGING DEPLOY**. No se declara T07
completada ni deployment realizado. Siguen pendientes Supabase real, Config
Vars Heroku, migración real, bootstrap real, deploy manual Heroku, publicación
Pages y smoke Staging.

## Archivos modificados

- `frontend/package-lock.json`
- `docs/evidence/sprint-01/TA-DEPLOY-001/README.md`
- `docs/evidence/sprint-01/TA-DEPLOY-001/t07-deployment-checklist.md`
- `docs/evidence/sprint-01/TA-DEPLOY-001/test-results/security-source-map-js.md`
