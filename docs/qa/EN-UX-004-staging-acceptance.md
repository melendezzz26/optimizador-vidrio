# EN-UX-004 — Runbook de aceptación en staging desplegado (NO EJECUTADO)

> Procedimiento para el operador autorizado. **No autoriza deploy, migraciones,
> cambios de config compartida ni consumo de inventario real.**
> Evidencia actual = CI efímero con PostgreSQL aislado, NO un staging desplegado.
> Referencias: [SPEC](../specs/SPEC-EN-UX-004-cancelacion-segura.md),
> [staging existente](../infrastructure/staging.md) y
> [contrato backend](https://github.com/melendezzz26/newglass-backend/blob/2afa9d72cecee74d4c61187ff15c74564e7dde3f/docs/contracts/optimization/comparison-v2.md).

## 0. Identidades y decisión de go/no-go

- Backend integrado: `2afa9d72cecee74d4c61187ff15c74564e7dde3f`.
- Frontend integrado antes de corrección: `7ac91f811e0aca82378d8ca4d862b3ebd080d290`.
- Frontend corrección UX: PR #14 (basado en `main`); título del aviso: PR #15
  **apilado sobre #14**, no sobre `main`. Ambos requieren revisión y merges separados.
- Documentación: PR #121 **basado en `integration-02`**, distinto de `main`.
- CI de integración: backend
  [43016873960](https://github.com/melendezzz26/newglass-backend/actions/runs/43016873960);
  frontend [43018881023](https://github.com/melendezzz26/newglass-frontend/actions/runs/43018881023),
  TA-040 150/150. Revalidar HEAD y CI de los PR correctivos antes de liberar.
- Nombrar propietario QA, supervisor de staging, ventana aprobada, identidad del
  entorno y rollback owner. Registrar los SHA realmente desplegados antes de actuar.

**NO-GO inmediato** si la base no es efímera y exclusivamente de prueba, contiene
pedidos/clientes reales o comparte Supabase; si la instancia admite tráfico real;
si las claves de conexión/dominio no se pueden verificar sin ambigüedad; si hay más
de un worker/dyno de admisión; si existe una comparación activa ajena; si falla CI,
el preflight de memoria/procfs, identidad de supervisor, backup o aislamiento.

## 1. Preflight reproducible sin publicación

Desde checkouts independientes y limpios (no el monorepo histórico), con versiones
de Python 3.11, Node 22 y PostgreSQL según CI:

```bash
# backend: confirmar que no hubo cambios en migraciones ni supervisor entre SHA
git rev-parse HEAD
python -m alembic heads
python -m scripts.check_comparison_environment

# frontend: verificar enlace explícito al backend y gates
git rev-parse HEAD
cat .github/backend-e2e.sha
npm ci
npm run test:unit
npm run test:component
npm run lint
npm run build
# La URL es un marcador no desplegable, sirve exclusivamente al build estático
VITE_API_URL=https://api.example.invalid npm run build:staging
npm run check:staging

# E2E independiente, servidor efímero: backend como carpeta hermana ../backend
# NUNCA definir DATABASE_URL de Supabase ni secretos staging para este comando
NEWGLASS_REQUIRE_POSTGRES=1 PYTHON_DOTENV_DISABLED=1 PLAYWRIGHT_CHANNEL=chromium \
  node scripts/run-e2e-phases.js
```

Verificar `0 failed`, `0` skips no aprobados y el resumen TA-040. No reutilizar
la base de datos creada por el harness como si fuese el staging desplegado.
`tests/e2e_server.py` configura y contiene `/__e2e__/comparison-worker/{mode}`
**solo en loopback**; esa ruta no puede exponerse al servicio staging público.

## 2. Preparación de staging desplegado (solo tras autorización aparte)

1. Crear **aplicación y PostgreSQL dedicados** para esta aceptación, con secreto
   JWT de pruebas distinto y CORS limitado al frontend de aceptación, sin
   identidad, lotes, órdenes, planchas o retazos reales. No apuntar nunca a la
   base staging compartida existente sin aprobación expresa y una comprobación
   independiente de aislamiento. Anotar IDs internos privados, no DSN/tokens.
2. Confirmar procedencia del deploy: la documentación histórica de Heroku usa
   `integration-02`; los repositorios integrados ahora son separados. Comprobar
   la conexión GitHub real del destino y el SHA del release en el runtime.
   **No** considerar iguales un commit del monorepo y uno del backend nuevo.
3. Backend `Procfile`: Uvicorn `--workers 1`, solo un dyno/instancia autorizada,
   Linux con procfs y presupuesto suficiente. Revisar límites de memoria y
   `python -m scripts.check_comparison_environment` desde runtime autorizado.
   Sin escalado durante pruebas; múltiples dueños requieren ADR nueva.
4. Ejecutar `python -m alembic heads` y `python -m alembic current` **solo
   con la URL ya comprobada por el responsable**. Si se necesita
   `upgrade head`, realizarlo exclusivamente en la base efímera con backup y
   autorización separada, y comprobar current después. Nada de `stamp`,
   `downgrade`, DDL manual o migración sobre Supabase compartido.
5. Configurar credenciales de operador/administrador **sintéticos** con permisos
   mínimos; registrar conteos iniciales de `pedidos`, `movimientos_inventario`,
   unidades de plancha/retazo y comparación. Conservar valores anonimizados.
6. Construir el frontend de aceptación contra la API HTTPS de esta misma
   aplicación usando `VITE_API_URL` y `npm run build:staging` + `check:staging`.
   **No** ejecutar todavía el workflow `Deploy Pages Staging`: es
   `workflow_dispatch`, restringido a `main`, y publica en `github-pages`
   compartido. Emplear destino separado con autorización y revisar CORS, TLS,
   rutas y ausencia de `localhost` en bundle. Nunca guardar secretos en VITE.
7. Registrar SHA, release ID, revisión Alembic, nombre del entorno y comprobación
   de `/health/live`, `/health/ready`, `/api/auth/me` y lectura autorizada.
   No continuar ante `RECOVERY_BLOCKED`, `OPTIMIZER_BUSY` inesperados o 5xx.

## 3. Captura de cada escenario

Usar para cada prueba una comparación/pedido sintético **nuevos**; registrar
`comparison_id` e IDs de pedido, `expected_version`, clave idempotente
**ficticia** asociada solo al intento, estado/detalles de métodos, release,
timestamp UTC, conteos y hashes de stock antes/después. No incluir JWT, cookies,
passwords ni DSN. Capturar HTTP redacted, UI, trazas de supervisor (token/PID
sanitizados) y filas de movimientos solo de la base efímera.

### CA-01 — Cancelar FF activo

- Aceptar comparación v2, confirmar seis referencias de ejecución.
- Esperar que FF tenga `dispatch_state=RUNNING` y `engine_started=true`;
  si termina demasiado rápido, usar dataset sintético más exigente, **sin**
  debilitar los motores ni crear un endpoint de test público. No marcar PASS
  si no se observa worker vivo.
- Abrir modal; identificar trabajo y pedidos; cancelar con permiso
  `optimization.execute`; capturar POST y GET usando token exclusivamente
  de staging controlado.
- Si el POST devuelve 202, exigir `cancel_state=REQUESTED`,
  `terminal=false`, `supervisor_stopped=false`; **nunca** mostrar Cancelada.
- Reconsultar hasta `CANCELLED` únicamente con
  `terminal=true`, `supervisor_stopped=true` y sin identidad de worker/hijo
  activo. No usar PID solo como prueba de identidad. Si no hay prueba de cierre,
  registrar FAIL/BLOCKED y detener.
- Revisar que BF/WF/HF/M5/M6-BS no llegaron a `started` tras la solicitud;
  permiso de selección/confirmación deshabilitado; cero movimientos de stock y
  pedidos `PENDIENTE` **solo después del cierre**.

### CA-02/03 — Cancelar BF/HF/M5/M6-BS y conservar previos

- Ejecutar **cada motor de interés en prueba independiente**:
  BF como baseline ya cubierto en integración, y tres casos focalizados
  HF, M5 y M6-BS; no repetir los E2E globales si no cambia código.
- Esperar persistencia verificable de los motores anteriores y estado RUNNING
  del motor objetivo. Guardar IDs/hashes de resultados persistidos.
- Solicitar cancelación; conservar exactamente resultados, métricas y geometría
  de cada motor completado. El objetivo activo queda CANCELLED y ninguno
  pendiente puede recibir `dispatching`/`started` posterior a la intención.
  Si M6-BS es el último, `no pending dispatch` es trivial: allí comprobar
  carrera de cierre, idempotencia y respeto a resultados anteriores.
- Ejecutar al menos un escenario **entre motores** justo después de persistir
  un resultado y antes de iniciar el siguiente, observando el orden de eventos.
  No falsear un PASS si la ventana temporal no se reproduce.

### CA-04/05 — Carrera, duplicados y recuperación

- Enviar dos POST con **misma** `Idempotency-Key` y versión esperada:
  mismo `comparison_id`, sin segundo efecto; otra clave da conflicto.
  Enviar solicitudes concurrentes con cuentas autorizada y no autorizada:
  trabajo ajeno no se revela (404) ni se señaliza.
- Simular pérdida de red del **navegador** durante POST desde DevTools o proxy
  de pruebas autorizado. No manipular el backend ni fingir 200/202. Restaurar
  red, recargar y consultar GET del trabajo y
  `GET /comparisons-v2/{id}/cancel`. Asegurar que no se inicia un trabajo nuevo,
  no se emite confirmación y se conserva la clave del intento pendiente.
- Carrera de conclusión: si todos los motores terminaron antes de atender la
  cancelación, esperar `COMPLETED_BEFORE_CANCEL` o rechazo por comparación ya
  terminal según el punto de carrera, nunca sobreescribir resultados ni reportar
  parada forzada inexistente.

### CA-07/08 — Reinicio **real** con worker vivo

**Solo en aplicación/dyno de staging totalmente descartable y aislado.**
Reservar una ventana sin otra carga. Registrar identidad verificada de supervisor,
worker y descendientes, revisión durable y estado de pedido.
Iniciar comparación sintética larga con worker identificado activo.
Solicitar cancelación y observar intención `REQUESTED` persistida.
El responsable del entorno reinicia **el servicio completo controlado** mediante
el mecanismo normal de la plataforma, sin enviar señales a PIDs manuales, sin
`kill -9` ni intervención sobre otro trabajo.

Al restaurarse, ejecutar lectura de snapshot y recuperación propia del sistema:
- Si hay procesos identificados aún vivos/no verificables, exigir bloqueo de
  admisión `RECOVERY_BLOCKED`, sin `terminal`, sin liberación de pedido ni
  cambios de inventario. Preservar evidencia y **no forzar limpieza del lease**.
- Si el sistema verificó ausencia de procesos y descendientes, se permite
  `CANCELLED` durable y pedido pendiente. Conservar resultados anteriores.
- Registrar comportamiento real según plataforma, identidad y logs
  sanitizados. Probar nuevo trabajo **solo** tras recuperación verificada.
- Si el reinicio deja identidades inconclusas, es FAIL/BLOCKED y requiere
  corrección antes del despliegue. Un timeout no es prueba de proceso muerto.

### CA-06/10/11/12 — Seguridad, continuidad e interfaz

- Permisos: usuario ajeno 404, usuario sin ejecutar no genera cancelación,
  doble clic solo una intención; comprobar IDs incorrectos y error recuperable.
- A lo largo de todos los casos, comparar stock, retazos y
  `movimientos_inventario` del entorno aislado; el conteo tras cancelación
  debe ser idéntico y no hay confirmación/corte real.
- Estado visual: modal, trabajo correcto, botón visible solo mientras puede
  cancelarse, 202 únicamente aviso de *solicitud*, luego **Cancelación
  confirmada** y resultado histórico consultable. No mostrar título genérico
  **Operación completada** como encabezado de la cancelación; esta regresión
  depende de frontend PR #15, apilado sobre #14.
- Regresión normal: ejecutar los seis motores FF/BF/WF/HF/M5/M6-BS hasta
  cierre natural, verificar diagnósticos y elegibilidad de cada método, selección
  y confirmación segura solo de soluciones elegibles. No confirmar stock real.
  Ejecutar desktop/móvil y teclado sobre frontend de aceptación.
- No mezclar `Pausar vista`, `Cancelar optimización`, `Liberar pedidos` y
  `Cancelar pedido`. Capturar mensajes separados para éxito, parcialidad,
  cancelación solicitada, cancelación final y fallo.

## 4. Matriz de ejecución y decisiones

| Caso | Fuente actual | Staging desplegado | Regla de aceptación |
|---|---|---|---|
| CI backend/frontend y contrato | PASS CI merge | NO EJECUTADO | SHA exacto y logs verdes |
| FF real, UI desktop/móvil, cierre | PASS E2E aislado | NO EJECUTADO | 202 ≠ cierre, no stock |
| BF con resultado FF previo | PASS integración backend | NO EJECUTADO | FF idéntico, sin WF |
| HF, M5 y M6-BS | Solo regresión normal | NO EJECUTADO | Cancelar cada uno en RUNNING |
| Entremotores y fin natural | PASS pruebas de carrera | NO EJECUTADO | sin reescribir resultados |
| GET durable y recarga | PASS CI aislado | NO EJECUTADO | mismo ID/estado |
| Doble clic y error HTTP | PASS componente | NO EJECUTADO | una clave/efecto |
| Red realmente desconectada | Simulación componente | NO EJECUTADO | reconexión sin falso cierre |
| Reinicio real con worker vivo | Simulación de recuperación/identidad | NO EJECUTADO | prueba de vida/lease |
| Órdenes, movimientos y stock | PASS DB de prueba | NO EJECUTADO | cero consumo; liberar después |
| Feedback cancelación explícita | PR #15 pending QA/merge | NO EJECUTADO | sin "Operación completada" |
| Six-motor normal | PASS regresión CI | NO EJECUTADO | seis resultados normales |

**No inferir PASS de staging a partir de CI.** Completar responsable, fecha UTC,
release/SHAs, pruebas, evidencias por caso y autor del cierre. FAIL en seguridad
de procesos/stock/órdenes/identidad implica **NO-GO**.

## 5. Reversión segura (solo después de deploy aprobado)

1. Si aparece fallo, **congelar nuevas aceptaciones** y no confirmar cortes.
   No reiniciar un supervisor con procesos vivos solo para acelerar rollback.
2. Consultar comparaciones activas/canceladas; registrar identidades y cierre
   seguro de workers. Si queda `RECOVERY_BLOCKED`, mantener servicio aislado,
   no retirar el lease ni publicar un estado falso. Notificar al responsable.
3. Redeplegar manualmente el **par compatible** de artefactos (backend y
   frontend aprobados anteriormente) en el destino **aislado**, registrando
   ambos SHAs y release IDs. Verificar contrato y CORS. El workflow de Pages
   publica manualmente y puede apuntar al `github-pages` compartido:
   NO ejecutarlo para un staging nuevo sin aprobación de destino/entorno.
4. No hacer downgrade automático de Alembic, `stamp`, DDL ni restauración
   improvisada. Cualquier restauración de base usa copia aislada y
   procedimiento de backup ya aprobado, con nueva autorización.
5. Validar `/health/live`, `/health/ready`, estado de procesos,
   pedidos e inventario antes/después; conservar el informe de incidente
   con IDs y sin secretos. No marcar rollback completo sin pruebas de cierre.

## 6. Criterio de Verified y aptitud de despliegue

**Verified de implementación**: PR #14 y #15 integrados en orden con CI
post-merge verde; PR #121 documental revisado en su base correcta; SPEC,
contratos y trazabilidad alineados. **No significa desplegado**.

**Staging Verified**: además, todos los casos de esta matriz ejecutados
contra una URL desplegada exclusiva, PostgreSQL efímero, workers reales,
cancelaciones HF/M5/M6-BS, red interrumpida y reinicio de servicio con
identidades comprobadas; evidencias auditables y sin efecto en stock real.

**Production-ready**: Staging Verified, rollback comprobado, autorización
humana explícita, ventana de despliegue y decisión de seguridad/operaciones.
No afirmar estar listo por CI o por un despliegue de pruebas no realizado.
