# Evidencia TA-035 T02: Smoke E2E de staging

| Dato | Valor |
|---|---|
| PBI / tarea | TA-035 T02 — Ejecutar smoke E2E del despliegue |
| Responsable | Fabricio Aguilar |
| Fecha de ejecución | 14/10/2026 00:35–01:55 |
| Frontend | https://melendezzz26.github.io/optimizador-vidrio/ · SHA 728c1dd · Deploy Pages Staging #5 (13/10/2026 17:25) |
| Backend | https://newglass-api-staging-5f52e8e9b00c.herokuapp.com · SHA 293a2a93 · Heroku release v12 (13/10/2026 16:35) · código idéntico a 728c1dd (PR #45 solo cambió docs/) |
| Navegador | Chrome 1xx · Windows 11 · Windows 11 |
| Cuentas | Una por rol (Administrador, Almacenero, Operario), entregadas por canal privado; no se registran credenciales. |
| Datos creados | Prefijo `SMOKE-` |

## Matriz

| ID | Rol | Paso | Resultado esperado | Resultado | Evidencia | Observación |
|---|---|---|---|---|---|---|
| SM-01 | — | Abrir `/health/live` de la API | `{"status":"ok"}` | PASS | screenshots/SM-01-health-live.png | |
| SM-02 | — | Abrir `/health/ready` de la API | `{"status":"ready"}` (API conectada a la BD) | PASS | screenshots/SM-02-health-ready.png | |
| SM-03 | — | Abrir el frontend | Carga la pantalla de login sin errores | PASS | screenshots/SM-03-frontend.png | |
| SM-04 | — | Login con contraseña incorrecta | Mensaje de error comprensible, sin detalles técnicos | PASS | screenshots/SM-04-login-invalido.png | |
| SM-05 | Administrador | Login | Entra y ve el módulo Usuarios | PASS | screenshots/SM-05-login-admin.png | |
| SM-06 | Administrador | Usuarios: listar, buscar y filtrar por rol | Lista con datos reales; filtros responden | PASS | screenshots/SM-06-usuarios.png | |
| SM-07 | Administrador | Crear usuario `SMOKE-...` y verlo en la lista | Mensaje de éxito; aparece en el listado | PASS | screenshots/SM-07-crear-usuario.png | |
| SM-08 | Almacenero | Login e Inventario: listar planchas y retazos | Ve inventario; no ve Usuarios | PASS | screenshots/SM-08-inventario.png | |
| SM-09 | Almacenero | Registrar plancha `SMOKE-` | Éxito; aparece en el listado | PASS | screenshots/SM-09-plancha.png | |
| SM-10 | Almacenero | Registrar retazo poligonal con el editor | Éxito; geometría guardada y visible | PASS | screenshots/SM-10-retazo.png | |
| SM-11 | Operario | Login, buscar o registrar cliente `SMOKE-` | Cliente disponible para el pedido | PASS | screenshots/SM-11-cliente.png | |
| SM-12 | Operario | Validación de stock al registrar pedido | Bloquea si una pieza no tiene stock candidato | BLOQUEADO | — | HU-008 no integrada en 293a2a9 |
| SM-13 | Operario | Registrar pedido multimaterial (2+ piezas de distinto material/espesor, una personalizada) | Pedido creado en estado PENDIENTE | PASS | screenshots/SM-13-pedido.png | |
| SM-14 | Operario | Recargar la página y recuperar el pedido (listado, filtro y detalle) | Persiste con cliente, piezas y geometrías | PASS | screenshots/SM-14-recuperar.png | |
| SM-15 | Operario | Editar el pedido PENDIENTE, guardar y volver a abrirlo | Cambio persistido; luego cerrar sesión | PASS | screenshots/SM-15-editar.png | |

## Resumen

| PASS | FAIL | BLOQUEADO |
|---|---|---|
| 14 | 0 | 1 |

## Observaciones

- Heroku: build fallido a las 16:34 y build correcto con deploy v12 a las 16:35 del 13/10/2026; el smoke se ejecuta sobre v12 (screenshots/heroku-activity.png).
- Frontend (728c1dd) y backend (293a2a9) tienen SHA distintos, pero el código es idéntico: PR #45 solo modificó docs/ (screenshots/deploy-pages-actions.png).
- SM-12 queda bloqueado hasta integrar y desplegar HU-008; se repite cuando esté disponible.
- Heroku Metrics reportó 5 errores críticos en las últimas 24 h (posiblemente asociados al build fallido de las 16:34 o a reinicios); no afectaron el smoke. Se informa al responsable de TA-035 T1 para revisión.
- Datos SMOKE creados en staging:
  - Usuario "SMOKE Usuario Prueba" (rol Operario).
  - Plancha Gris 8 mm 2440 × 1830 mm, cantidad 1.
  - Retazo cuadrilátero 600 × 400 mm (4 lados, ángulo fijado en V2 = 90°), Gris 8 mm.
  - Cliente "SMOKE Cliente Prueba".
  - Pedido #<id>: 2 piezas Gris 8 mm 500 × 300 + 1 pieza poligonal <material>; estado PENDIENTE. En SM-15 se editó la cantidad de la pieza 1 (2 → 3); persistió tras recargar y el logout fue correcto.