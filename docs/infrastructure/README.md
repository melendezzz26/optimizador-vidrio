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

Posteriormente, el workflow se ejecutó en GitHub Actions mediante el Pull
Request #8. Los jobs `backend` y `frontend` finalizaron correctamente y el
Pull Request mostró el estado **Ready to merge** después de completar los
checks.

Esta validación remota se registra por separado de las comprobaciones locales
anteriores en la
[evidencia final de EN-001](../evidence/sprint-01/EN-001/en-001-final-validation.md).

## Configuración backend — TA-DEPLOY-001 T02

`app/shared/config/` carga una sola vez el archivo opcional `backend/.env`
con `override=False`. Las variables del proceso prevalecen. No se necesita
un archivo `.env` en Staging; la configuración debe suministrarse externamente.
No se incluyen secretos ni se configura ningún servicio remoto en T02.

| Variable | Contrato |
|---|---|
| `DATABASE_URL` | Obligatoria al utilizar persistencia o Alembic, sin fallback. Se conserva íntegra, incluidos parámetros TLS y codificación de contraseña. |
| `SECRET_KEY` | Obligatoria al importar autenticación. Ausente, vacía o solo espacios falla sin imprimir su valor. El ejemplo la deja vacía intencionalmente; generar una clave propia fuera de Git. |
| `TOKEN_MINUTOS` | Entero positivo, default `480`. Rechaza formatos inválidos y duraciones que exceden el rango de fechas. |
| `CORS_ORIGINS` | Orígenes HTTP/HTTPS separados por comas. Trim, omisión de entradas vacías y eliminación de duplicados. Rechaza wildcard, credenciales, rutas, query, fragmento y puertos inválidos. |
| `DB_POOL_SIZE` | Opcional, entero >= 1. Tamaño del pool PostgreSQL por proceso. |
| `DB_MAX_OVERFLOW` | Opcional, entero >= 0. Conexiones adicionales; `0` deshabilita overflow. |
| `DB_POOL_TIMEOUT` | Opcional, segundos enteros >= 1 para esperar una conexión del pool. No es timeout de consulta SQL. |
| `DB_CONNECT_TIMEOUT` | Opcional, segundos enteros >= 1, enviados a psycopg mediante `connect_args`. No es timeout de consulta SQL. |

Si `CORS_ORIGINS` no existe, desarrollo conserva `http://localhost:5173` y
`http://127.0.0.1:5173`. Si existe pero solo contiene entradas vacías, no permite
ningún origen; no vuelve a localhost. En Staging es obligatorio definir
explícitamente el origen HTTPS aprobado de Pages, sin `/optimizador-vidrio/`
ni barra final. No se ha incorporado ningún dominio real. Se mantienen
`allow_credentials=False`, los métodos GET/POST/PATCH/DELETE/PUT y los headers
Authorization/Content-Type. El fallback local no detecta el entorno Staging:
su configuración explícita deberá verificarse durante T07.

Se mantiene un engine compartido por proceso con `pool_pre_ping=True`.
Sin las opciones `DB_*`, SQLAlchemy y el driver conservan sus defaults.
Las opciones de pool y `connect_timeout` se aplican a PostgreSQL; SQLite y
otros motores no reciben estos parámetros para mantener compatibilidad.
Las variables presentes pero vacías o inválidas se rechazan, incluso si
el motor no las utiliza. No se admiten límites ilimitados (`pool_size=0`
o `max_overflow=-1`) mediante estas variables.

Los valores de Staging deben elegirse tras revisar plan, procesos/dynos y
límites reales de Supabase en T04/T07: T02 no fija cifras recomendadas.
`DATABASE_URL` deberá incluir TLS según el endpoint aprobado, por ejemplo
`sslmode=require` cuando corresponda; el código no agrega certificados ni
fuerza/reemplaza `sslmode`. Preservar un parámetro no demuestra TLS remoto.

Alembic recibe la misma configuración externa, usa `NullPool` y aplica el
timeout de conexión PostgreSQL si está definido, sin opciones de QueuePool.
Solo al pasar la URL a ConfigParser se escapa `%` como `%%`; al leerla se
recupera la URL original. **No guardar `%%` en la variable del entorno ni
modificar la contraseña para compensar ConfigParser.**

La importación diferida de persistencia permanece: el proceso puede cargar
sin abrir una conexión, y `DATABASE_URL` se exige al cargar persistencia.
Este cambio no añade health checks ni valida conectividad. Heroku suministra
`PORT` al comando web; no corresponde añadirlo al ejemplo del backend.

Pruebas y límites de la validación local en
[T02 configuración Staging](../evidence/sprint-01/TA-DEPLOY-001/test-results/t02-config-staging.md).
