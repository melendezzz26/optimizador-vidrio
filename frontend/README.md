# Frontend de NewGlass

Interfaz web con React y Vite, organizada progresivamente por funcionalidades.
El entorno local revisado utiliza Node.js **22.16.0**, compatible con los
requisitos del lockfile actual. Los comandos se ejecutan desde `frontend/`.

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

Todavía no hay un script `npm test`. Lint y build no sustituyen las pruebas
funcionales que se incorporen con cada feature.

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
    components/       Código actual conservado temporalmente
    pages/            Código actual conservado temporalmente
    assets/
```

La funcionalidad nueva se desarrolla en `src/features/<feature>/`.
El frontend no replica las capas Clean Architecture del backend: componentes,
hooks, estado y acceso a API se organizan dentro de cada feature según necesidad.
`src/shared/` se reserva para código reutilizable por varias features.

`src/components/Login.jsx` y `src/pages/NuevoPedido.jsx`, sus estilos y sus imports
permanecen temporalmente en las rutas actuales hasta que los responsables los
migren con validación. Esta fase únicamente reserva carpetas; no incorpora
implementaciones ni modifica `App.jsx`.

Consultar la [guía de desarrollo](../CONTRIBUTING.md), las
[convenciones de features](src/features/README.md) y los
[límites de shared](src/shared/README.md).
