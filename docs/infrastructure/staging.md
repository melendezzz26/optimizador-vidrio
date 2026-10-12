# NewGlass — procedimiento controlado de Staging

SPEC: [TA-DEPLOY-001](../specs/SPEC-TA-DEPLOY-001-staging.md), Reviewed.
Este documento prepara una ejecución humana posterior; no certifica servicios
remotos ni autoriza por sí solo migraciones, bootstrap o publicación.

## Configuración y destino

Aplicación: `newglass-api-staging`, GitHub conectado, deploy backend manual,
automatic deploy desactivado. Seleccionar un SHA integrado/aprobado de
`integration/sprint-01`, con los checks de release aprobados. Mantener un
proceso web; no se requieren Redis, workers, scheduler o Heroku Postgres.

Config Vars externas: `DATABASE_URL`, `SECRET_KEY`, `TOKEN_MINUTOS`,
`CORS_ORIGINS` y opciones `DB_*` descritas en [infraestructura](README.md).
Heroku proporciona `PORT`. No crear `.env` remoto ni copiar secretos a Git,
capturas, comandos con valores literales, artifacts o logs de evidencia.

`DATABASE_URL` debe proceder del endpoint aprobado de PostgreSQL Staging,
aislado de bases compartidas. Conservar `postgresql+psycopg://` y parámetros
TLS del proveedor: por ejemplo `sslmode=require` cuando corresponda, o
verificación de certificado según la configuración aprobada. No construir
el hostname del pooler a mano. Codificar caracteres reservados de contraseña
como URL; no añadir `%%` por ConfigParser (T02 lo resuelve internamente).

Decisión a validar en T07: conexión directa si el runtime alcanza su endpoint
IPv6/IPv4; Session Pooler como alternativa de conexión persistente compatible
con la red. Registrar región, endpoint/modo elegido y motivo sin publicar DSN.
No asumir que transaction pooling sea intercambiable: necesita revisar
prepared statements y semántica de sesión antes de seleccionarlo.

Antes de fijar pool/timeout, revisar conexiones disponibles del plan, número
de procesos/dynos y margen para migraciones, administración y readiness.
Presupuesto por proceso: pool_size + max_overflow, más conexiones auxiliares.
Definir tiempos finitos de conexión y espera; no inventar límites del plan.
`pool_pre_ping` está habilitado. Readiness tiene plazo HTTP de 3 s y permite
un probe en curso; PostgreSQL aplica también timeout de sentencia de 3 s.
Timeout de conexión/pool no equivale a timeout SQL general de la aplicación.

Verificar TLS efectivo desde el runtime autorizado, DNS/ruta de red y políticas
de exposición de Supabase. El backend usa PostgreSQL, no claves anon/service_role.
Revisar Data API, grants y RLS para que no exista un acceso alternativo que
eluda los permisos FastAPI. Nada de esto se declara verificado localmente.

## Prechecks de Alembic (solo tras autorización del destino real)

1. Confirmar SHA, entorno y responsable. Verificar que el destino es el
   Staging autorizado; inspeccionar host/BD de forma privada, sin conservarlos
   en evidencia pública. Detenerse ante cualquier ambigüedad.
2. Registrar revisión actual, historial/head esperados y tablas/datos existentes.
   Identificar qué registros se deben preservar y cómo se compararán antes/después.
3. Confirmar backup y procedimiento de restauración probado, responsable y
   ventana operativa. Para una base nueva, confirmar que realmente está vacía.
4. Confirmar ensayo en PostgreSQL aislado y todas las precondiciones siguientes.
5. No ejecutar seed/admin antes de completar migraciones: algunas revisiones
   requieren tablas vacías. No habilitar tráfico de escritura durante el cambio.

Cadena aprobada, sin revisiones nuevas:

```text
9b9f04eb67f6 -> c4e8a1f2b3d5 -> e1a2b3c4d5f6 -> f2b3c4d5e6a7
-> a3c4d5e6f7b8 -> b4d5e6f7a8c9 -> 1c8754481a08 -> d6e7f8a9b0c1
-> ef6564220e70 -> fa014e1a2b3c
```

Precondiciones: HU-003 rechaza usuarios heredados sin DNI; R1 comprueba
identidad, geometría y consistencia de los datos; R2 exige configuraciones
vacías; R3 exige ejecuciones/métricas vacías; R4 exige métricas vacías.
TA-013 valida tipos/espesores y carga seis tipos con 28 combinaciones;
HU-006 valida materiales, FK y conservación de conteos. Un head distinto o
datos incompatibles requieren revisión; no eliminarlos para forzar el upgrade.
Las migraciones consultan datos: generar SQL offline no sustituye el ensayo.

Comandos futuros desde `backend/`, con entorno ya suministrado de forma segura:

```sh
python -m alembic heads
python -m alembic history
python -m alembic current
# SOLO después de confirmar destino, precondiciones y autorización:
python -m alembic upgrade head
python -m alembic current
```

El único head y el current final deben ser `fa014e1a2b3c`. Antes de un destino
nuevo, current puede estar vacío. Comparar catálogo y registros acordados;
no afirmar ausencia de pérdida de datos sin comparación concreta. Guardar
resultados sanitizados con fecha, SHA, revisión anterior/posterior y responsable.

## Bootstrap auditado

`python seed.py`: `crear_roles()` consulta por nombre y agrega solamente roles
ausentes (Administrador, Almacenero, Operario), hace commit y cierra sesión.
Es repetible secuencialmente; no está diseñado para ejecuciones concurrentes.
No crea usuarios ni modifica descripciones de roles preexistentes.

`python -m scripts.create_first_admin`: pide confirmación `CREAR`, nombres,
apellidos, DNI y contraseña mediante getpass con repetición; valida con los
casos de uso actuales y bcrypt. Requiere rol Administrador y rechaza la creación
si ya existe un administrador activo. Permite crear si solo hay uno inactivo;
no asumir idempotencia de creación de usuarios. Ejecutar una sola vez y sin
concurrencia. Muestra host/base para confirmación privada: sanitizar evidencia.

Orden humano posterior: migrar, verificar catálogo, cargar roles, crear un
administrador con datos controlados de Staging y comprobar login/permisos.
No usar identidades personales reales; gestionar y cambiar la credencial inicial
según el acuerdo operativo. No pasar contraseña como argumento, variable VITE
o texto de evidencia. Ningún bootstrap de Staging se ejecuta en CI de PR.

## Recuperación y rollback

Un rollback de aplicación consiste en redeplegar el SHA backend anterior y
republicar el artefacto frontend anterior compatible. No revierte PostgreSQL.
R1/R2/R3/R4 rechazan downgrade automático; no recomendar `downgrade base`.
Si falla un precheck o upgrade, detener publicación, conservar diagnóstico
sanitizado y verificar revisión/transacción antes de cualquier nuevo intento.
Si hace falta recuperar datos, usar el backup/procedimiento aprobado y validar
su resultado; no improvisar DDL ni borrar datos. **Está prohibido usar
`alembic stamp` para ocultar divergencias.**

## Validación de release pendiente

T07 requiere backend completo, unit/component, lint/build y Playwright aprobados
antes del despliegue. Después: live/ready, ausencia de db-test, login y `/me`,
lectura de inventario, preflight permitido/denegado, carga/recarga de Pages bajo
`/optimizador-vidrio/` y editor por navegación SPA, sin peticiones a localhost.
Registrar SHA backend/frontend, revisión Alembic, fecha y resultados sin secretos.
T04 solo aporta ensayo local/procedimiento; CA-08 no queda cumplido remotamente.
