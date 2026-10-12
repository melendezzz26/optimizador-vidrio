# Evidencia HU-003 T04 y T05: Vista de gestión de usuarios

| Dato | Valor |
|---|---|
| PBI / tareas | HU-003 T04 (búsqueda y filtros) y T05 (alta/edición solo bajo acción) |
| SPEC | docs/specs/SPEC-HU-003-T04-T05-vista-gestion-usuarios.md |
| Responsable | Fabricio Aguilar |
| Fecha | 2026-10-11 |
| Entorno | Local, Windows (frontend con Vite y Vitest; backend con Python y pytest) |
| Rama | feature/HU-003-T04-T05-vista-gestion-usuarios |
| Commits | 8790758 (SPEC), f9e5e61 (lógica de filtros), 8a4557d (T04), 122e800 (T05) |

## 1. Qué se entrega

- **T04:** búsqueda por usuario, nombres y apellidos (sin distinguir tildes ni mayúsculas) y filtros por rol y estado, combinables, con contador de resultados, botón "Limpiar filtros" y estados vacíos diferenciados ("sin datos" y "sin resultados"). Lógica en `userFilters.js` (función pura) y controles en `UsersFilters.jsx`.
- **T05:** la pantalla empieza en el listado. "Nuevo usuario" y "Editar" abren el formulario en lugar del listado; "Guardar" y "Cancelar" vuelven al listado conservando el mensaje de resultado y los filtros. Usa `useManagementView` (TA-034 T02).
- Sin cambios de backend, API ni BD. El CRUD existente se conserva.

## 2. Pruebas automatizadas

| Procedimiento | Resultado esperado | Resultado obtenido | Archivo |
|---|---|---|---|
| `npx vitest run --reporter=verbose src/features/users` | Todas pasan | 23 passed (4 archivos) | test-results/vitest-users.txt |
| `npx vitest run` (suite completa) | Todas pasan | 127 passed (15 archivos) | test-results/vitest-suite-completa.txt |
| `npm run lint` | Sin errores | Pass | test-results/lint.txt |
| `npm run build` | Build correcto | Pass | test-results/build.txt |
| `python -m pytest -q` (backend) | Sin fallos | 747 passed, 343 skipped, 1 warning in 15.95s | test-results/pytest.txt |

## 3. Trazabilidad con los criterios de aceptación

| CA | Prueba automatizada | Caso manual |
|---|---|---|
| CA-01 Formulario no permanente | UsersPageManagement: "al entrar muestra el listado y no el formulario" | CP-HU003-T05-01 |
| CA-02 Búsqueda y filtros combinables con estado vacío | userFilters (8 casos) y UsersPageFilters (5 casos) | CP-HU003-T04-01 a 04 |
| CA-03 Validación con feedback compartido | UsersPageManagement: "usuario duplicado…" | CP-HU003-T05-03 |
| CA-04 Restricciones por rol | Sin cambios: la API sigue con `require_permission` (cubierto por pytest) | CP-HU003-T05-05 |

## 4. Casos manuales

| ID | Caso | Esperado | Obtenido | Evidencia |
|---|---|---|---|---|
| CP-HU003-T04-01 | Buscar "perez" | Encuentra "Pérez"; contador actualizado | Pass | screenshots/02-busqueda.png |
| CP-HU003-T04-02 | Rol + Estado | Solo usuarios que cumplen ambos | Pass | screenshots/03-filtros-combinados.png |
| CP-HU003-T04-03 | Combinación sin coincidencias | EmptyState "sin resultados" | Pass | screenshots/04-sin-resultados.png |
| CP-HU003-T04-04 | Limpiar filtros | Vuelve el listado completo | Pass | — |
| CP-HU003-T05-01 | Entrar al Panel de roles | Listado sin formulario | Pass | screenshots/01-vista-inicial.png |
| CP-HU003-T05-02 | Nuevo usuario → Cancelar | Formulario reemplaza al listado; Cancelar vuelve con filtros conservados | Pass | screenshots/05-formulario-nuevo.png |
| CP-HU003-T05-03 | DNI duplicado | Error junto al DNI; formulario abierto | Pass | screenshots/06-usuario-duplicado.png |
| CP-HU003-T05-04 | Registrar y editar | Vuelve al listado con mensaje verde | Pass | screenshots/07 y 08 |
| CP-HU003-T05-05 | Entrar con un rol no Administrador | No se ofrece el Panel de roles | Pass | Manual |
| CP-HU003-T05-06 | Teclado | Al abrir, el foco va al título del formulario; Tab recorre los campos | Pass | Manual |

Las capturas no muestran tokens, contraseñas ni DNI reales.

## 5. Observaciones

- Al cerrar el formulario, el foco vuelve al inicio de la página y no al botón que lo abrió. Es una mejora de accesibilidad pendiente.
- El filtrado se hace en el navegador porque la API ya devuelve todos los usuarios y el volumen es pequeño. Si crece, se evaluará paginación en el backend.