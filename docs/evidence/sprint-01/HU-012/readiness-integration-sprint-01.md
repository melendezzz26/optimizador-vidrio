# Readiness de integration/sprint-01 para despliegue

**Clasificación: NO LISTO para despliegue público tal como está configurado.**

Revisión no destructiva del 11/10/2026 (fecha del usuario), referencia remota
`bf6ca1a`. La rama local de integración no se modificó. Las verificaciones de ejecución
se realizan en la feature T03 que incorpora esa referencia, no en un checkout puro de
integración. Los resultados no certifican un entorno remoto ni reemplazan su smoke test.

## Condiciones que deben resolverse antes del despliegue

1. **Origen del frontend:** `backend/main.py` admite exclusivamente
   `http://localhost:5173` y `http://127.0.0.1:5173`. Un frontend público en otro origen
   queda bloqueado por CORS. Configurar el origen real mediante un cambio revisado,
   o documentar/probar una topología de mismo origen con proxy de `/api`.
   PUT y DELETE ya están habilitados junto con GET, POST y PATCH.
2. **Diagnóstico público:** `/db-test` no tiene autenticación y devuelve la versión
   de PostgreSQL. Retirarlo, protegerlo o impedir su exposición en el proxy antes
   de publicar. No se utilizó contra ninguna base compartida.
3. **Configuración del destino:** aún deben provisionarse DATABASE_URL, SECRET_KEY,
   dominio/TLS, proceso backend y hosting estático. No se inspeccionaron secretos
   locales ni remotos ni se verificó el esquema de producción.
4. **Si el despliegue incluye T03:** revisar y aprobar su PR hacia integración;
   `bf6ca1a` todavía no contiene esa funcionalidad. No se realizó ese merge.

Estas condiciones pertenecen al despliegue; no se cambian lateralmente en T03.

## Backend

| Aspecto | Hallazgo / acción previa |
|---|---|
| Arranque documentado | `python -m uvicorn main:app --reload` desde `backend/`, válido para desarrollo. |
| Arranque del servicio | Configurar `python -m uvicorn main:app --host 0.0.0.0 --port <puerto>` sin `--reload`, bajo el supervisor/plataforma elegida. El puerto debe coincidir con el proxy. |
| Persistencia | `DATABASE_URL` usa SQLAlchemy/psycopg; configurar conexión, TLS y permisos del destino fuera de Git. |
| Firma de sesiones | `SECRET_KEY` obligatoria; no hay valor de producción predeterminado. `TOKEN_MINUTOS` debe ser positivo; ejemplo 480. No usar valores de `.env.example`. |
| Rutas | Routers `/api/auth`, `/api/users`, `/api/inventory`, `/api/orders`, `/api/clients` registrados en `main.py`. Revisar los prefijos del proxy. |
| Health | GET `/` confirma que el proceso HTTP responde; no comprueba disponibilidad de BD. Diseñar/comprobar readiness de BD sin exponer `/db-test`. |
| Dependencias | `backend/requirements.txt` fija versiones. Instalación limpia del destino y compatibilidad con su Python pendientes. |
| Runtime | Validación local Python 3.14.7; README dice 3.11.9 y CI configura 3.11. No afirmar equivalencia sin CI/instalación limpia. |

## Frontend

- `frontend/.env.example` documenta `VITE_API_URL`. `src/shared/apiUrl.js` la utiliza
  y, si falta, apunta a `http://127.0.0.1:8000`. Debe fijarse **al construir** el
  frontend para que los navegadores no intenten acceder a su propio localhost.
- Instalación reproducible: `npm ci`; construcción: `npm run build`. Resultado:
  `frontend/dist/`. No versionar `node_modules` ni `dist`.
- Servir `dist` con hosting estático y fallback a `index.html` para `/editor-pieza`.
  La navegación principal se controla en App con estado; la entrada manual
  `hu007-t01.html` es de desarrollo/pruebas y no forma parte del build principal.
- `npm run dev` y `npm run preview` no constituyen una configuración de producción.
- `package-lock.json` está versionado y no se cambió en T03. La validación local usa
  Node 24.21.0/npm 11.19.0. Revisar el runtime elegido con los engines instalados.
- Observación de rendimiento: el fondo heredado pesa aproximadamente 3.24 MB;
  se conserva en este cierre. No se certificó rendimiento en redes de taller.

## Base de datos y migraciones

Un solo head: **`ef6564220e70`**. Ninguna migración nueva por integración reciente
ni por T03. Cadena comprobada mediante `alembic heads` y `alembic history`:

```text
9b9f04eb67f6 -> c4e8a1f2b3d5 -> e1a2b3c4d5f6 -> f2b3c4d5e6a7
-> a3c4d5e6f7b8 -> b4d5e6f7a8c9 -> 1c8754481a08 -> d6e7f8a9b0c1
-> ef6564220e70
```

Antes de migrar el destino: respaldo, revisión autorizada de su revisión Alembic
actual y de las precondiciones/datos de las migraciones, prueba en staging y plan
de recuperación. Solo entonces ejecutar `python -m alembic upgrade head` desde
`backend/` con la conexión del entorno autorizado. **Ese comando no se ejecutó
contra producción ni Supabase durante este trabajo.**

Los pedidos históricos conservan `id_cliente NULL`; no se crean clientes ficticios.
T03 exige cliente en el POST nuevo y permite GET/edición de piezas de históricos.
No hacer un backfill ni establecer NOT NULL sin una decisión posterior de negocio.
Los catálogos/roles y el primer administrador necesitan preparación autorizada;
no ejecutar seeds ni `scripts.create_first_admin` como parte de este cierre.

## Seguridad, integración y automatización

- Inspección de textos versionados de `bf6ca1a`: no se detectaron claves privadas,
  tokens GitHub, JWT literales ni `.env` real versionado. La única URL con contraseña
  hallada fue el ejemplo ficticio de `backend/.env.example`. Es una búsqueda acotada
  por patrones, no una auditoría del historial ni un análisis de vulnerabilidades.
  Registro: [security-scan.json](test-results/t03/post-integration/security-scan.json).
- La cuenta usada en E2E/inspección es sintética, creada exclusivamente en
  PostgreSQL temporal; no corresponde a credenciales de producción.
- T01/T02 y HU-006/HU-007 forman parte de la base heredada. HU-013, saneamiento UI
  y HU-003 T04/T05 llegaron en los PR #36/#37/#38. No hay conflictos ni múltiples
  heads. La rama remota HU-014 existe, pero no se ha establecido que sea requisito
  para este despliegue; confirmar el alcance del release con el equipo.
- CI corre en PR y push a `main`, no en push directo a integración. El job frontend
  ejecuta lint/build, no unit/component/E2E. El job backend ejecuta pytest sobre
  Ubuntu/Python 3.11. El resultado local de Windows no sustituye ese resultado CI.
- README backend aún describe una suite sin PostgreSQL y README/testing frontend
  un E2E sin login/backend. Son descripciones anteriores; utilizar los comandos
  y el aislamiento de la [evidencia T03](t03-asociar-cliente-pedido.md).

## Secuencia de preparación pendiente

1. Revisar el PR T03 y su CI; integrar únicamente tras aprobación del equipo.
2. Resolver CORS/topología y exposición de `/db-test` en trabajo de despliegue.
3. Configurar secretos, TLS, puertos, procesos y `VITE_API_URL` del destino.
4. Instalar dependencias en el runtime final, construir y validar en staging.
5. Revisar y respaldar BD; aplicar migraciones solo con autorización del despliegue.
6. Ejecutar smoke de login/permisos, consulta/alta de cliente, pedido multimaterial,
   editor HU-007, lectura y edición preservando cliente/históricos, CORS y health.

No se desplegó, no se modificó integración/main y no se aplicaron migraciones remotas.
