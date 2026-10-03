# Documentación de infraestructura

Ubicación para describir entornos, servicios y procedimientos operativos cuando
se incorporen al proyecto. La preparación local vigente está en los README de
[backend](../../backend/README.md) y [frontend](../../frontend/README.md).

Cada procedimiento debe identificar su entorno de aplicación, requisitos,
comandos y forma de validación, distinguiendo lo propuesto de lo ejecutado.
Referenciar variables por nombre y usar ejemplos ficticios; no incluir `.env`,
credenciales ni secretos.

## Integración continua

El workflow [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml) se activa
en Pull Requests y en push a `main`. Ejecuta dos jobs independientes:

- Backend: Python 3.11, instalación de dependencias y `python -m pytest -q`.
- Frontend: Node 22, `npm ci`, `npm run lint` y `npm run build`.

No usa secretos ni una base de datos externa, ni ejecuta migraciones o despliegues.
La configuración fue validada estáticamente y las comprobaciones de pytest,
lint y build se ejecutaron localmente.

Todavía no se ha observado una ejecución real exitosa en GitHub Actions.
Esa comprobación se realizará al abrir el Pull Request; la validación local
no acredita el resultado del runner remoto.
