# Frontend de NewGlass

Interfaz web con React y Vite, organizada progresivamente por funcionalidades.
El entorno de pruebas HU-007 utiliza Node.js **24.21.0** y npm **11.19.0**.
Para las nuevas dependencias de pruebas, usar Node 22.22.2+, 24.15.0+ o 26+,
según los rangos de sus `engines`; Node 22.16.0 del entorno anterior ya no basta.
Los comandos se ejecutan desde `frontend/`.

## Instalación

```bash
npm ci
```

`npm ci` instala las versiones registradas en `package-lock.json`. Conservar ese
archivo en Git; los cambios de dependencias corresponden a tareas específicas.
Si PowerShell bloquea `npm.ps1`, usar `npm.cmd` con los mismos argumentos.

## Desarrollo y validación

```bash
npm run dev
npm run lint
npm run build
```

- `dev`: inicia Vite; consultar la URL indicada por la terminal.
- `lint`: ejecuta ESLint sobre el proyecto.
- `build`: genera el sitio en `dist/`, directorio ya ignorado por Git.

Para revisar localmente el build:

```bash
npm run preview
```

## Pruebas HU-007 T01/T02

En Windows local, instalar Google Chrome estable y ejecutar:

```powershell
npm.cmd run test:e2e
# O todas las suites:
npm.cmd test
```

`test` ejecuta en orden `test:unit` (las 38 pruebas existentes con `node:test`),
`test:component` (Vitest + React Testing Library en jsdom) y `test:e2e`
(Playwright). Cada script también puede ejecutarse por separado con `npm run`.
Vitest reutiliza la configuración Vite y solo descubre pruebas de componente;
no recoge las suites de Node ni de Playwright.

Playwright inicia y detiene Vite en `http://127.0.0.1:5173`, necesita ese puerto
libre y abre `/hu007-t01.html`. No requiere Login, backend, credenciales ni BD.
Prueba el flujo frontend en Google Chrome de escritorio y móvil emulado. No representa
el E2E completo de NewGlass ni registra el pedido.

La configuración usa por defecto `channel: 'chrome'`, el
[canal oficial de Playwright](https://playwright.dev/docs/browsers#google-chrome--microsoft-edge)
para Google Chrome estable instalado. No requiere descargar Chromium ni definir
variables de entorno en Windows local, y no contiene rutas absolutas al ejecutable.
Se conservan los nombres `chromium-desktop` y `chromium-mobile` para mantener la
trazabilidad, con los mismos viewports, casos, servidor y artefactos.

Una futura CI puede instalar el Chromium oficial de Playwright y seleccionarlo
con la variable opcional `PLAYWRIGHT_CHANNEL=chromium`. Ejemplo para Linux CI:

```bash
npm ci
npx playwright install --with-deps chromium
PLAYWRIGHT_CHANNEL=chromium npm run test:e2e
```

Esa alternativa requiere descarga y dependencias del sistema; no fue ejecutada
en esta validación local. Si CI mantiene el valor predeterminado, deberá disponer
de Chrome estable. Una variable `PLAYWRIGHT_CHANNEL` existente prevalece sobre
el valor predeterminado; quitarla para volver a Chrome.

Incidencia de entorno previa: "Descarga de Chromium de Playwright fallida por
timeout; ejecución local realizada posteriormente con Google Chrome instalado."
El error de ejecutable ausente impide iniciar los E2E y no demuestra un fallo
funcional de NewGlass.

Se genera
`playwright-report/` (abrir con `npx playwright show-report`); las trazas y capturas
se conservan en `test-results/` únicamente ante fallos. Son artefactos ignorados.
No hay sleeps ni reintentos automáticos para ocultar fallos.

La [evidencia HU-007](../docs/evidence/sprint-01/HU-007/t01-t02-pruebas-frontend.md)
registra casos, criterios SPEC, resultados y limitaciones. Lint y build siguen
siendo verificaciones adicionales, no pruebas de comportamiento.

## Organización por features

```text
src/
    features/
        authentication/
        users/
        inventory/
        orders/
        optimization/
        results/
        configuration/
    shared/
    pages/            Código actual conservado temporalmente
    assets/
```

La funcionalidad nueva se desarrolla en `src/features/<feature>/`.
El frontend no replica las capas Clean Architecture del backend: componentes,
hooks, estado y acceso a API se organizan dentro de cada feature según necesidad.
`src/shared/` se reserva para código reutilizable por varias features.

El inicio de sesión ya se migró a `src/features/authentication/` (HU-001).
`src/pages/NuevoPedido.jsx`, sus estilos y sus imports permanecen en la ruta
actual hasta que su responsable los migre con validación.

## Conexión con el backend

El frontend llama a la API en `http://127.0.0.1:8000`. Para usar otra dirección,
copiar `.env.example` como `.env.local` y ajustar `VITE_API_URL`. El backend
solo acepta peticiones desde `http://localhost:5173` y `http://127.0.0.1:5173`.

Consultar la [guía de desarrollo](../CONTRIBUTING.md), las
[convenciones de features](src/features/README.md) y los
[límites de shared](src/shared/README.md).
