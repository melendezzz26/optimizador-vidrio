# Ajuste del editor geométrico y navegación — 13/10/2026

Evidencia histórica de la primera iteración, conservada con sus resultados.
El contrato final de ángulos, el retiro del reescalado automático y la
confirmación del retest manual están en
[Correctivo angular y JSON de retazo](correctivo-angular-json.md).

Rama: `feature/TA-036-saneamiento-funcional`. Cambios locales sobre
`fa13b0020fcee57a8368d54b0d4e980a41630d3e`.
Solicitud posterior a la revisión técnica: lados editables individualmente,
ángulo fijado para cuadriláteros, pentágono irregular, mismo editor en retazos
y navegación de módulos exclusivamente desde sidebar.

## Comportamiento comprobado

| Caso solicitado | Resultado y evidencia |
| --- | --- |
| Triángulo 50/70/65 | Los tres campos son independientes. Ángulos derivados de los vértices; V2 = 63,026945°. Pruebas unitarias, componente, navegador y POST/GET real local. |
| Triángulo 10/10/30 | Rechazado: el lado mayor debe ser menor que la suma de los otros. No hay geometría guardable ni ángulos obsoletos. Pruebas unitarias, componente y navegador. |
| Cuadrilátero 120/73/91/108 | Modo de ángulo interior V2 (entre S1/S2). Pasar de 85° a 110° cambia vértices conservando las cuatro longitudes. Un ángulo incompatible produce explicación de configuración y retira el resultado previo. Reapertura conserva configuración. |
| Pentágono 80/115/63/92/71 | Construcción convexa válida con los cinco lados. La UI declara la restricción cíclica: vértices sobre una circunferencia. No afirma unicidad desde lados. |
| Retazo poligonal | `RegistrarRetazoForm` sigue importando el mismo `CustomPieceEditor`. Regresión de formulario verifica cuatro lados, V2 = 110° y payload `geometria = { type: POLIGONO_CONVEXO, vertices_mm }`. |
| Navegación | Botones de módulos únicamente en Sidebar; permisos y estado activo conservados. Header de sesión contiene identidad, rol y cerrar sesión. Se prueba navegación por clic/teclado y cierre. E2E comprueba header y sidebar con sesión real. |

`constrainedGeometry.js` construye vértices a partir de lados **y la
configuración elegida**. Normaliza longitudes para evitar desbordamiento,
comprueba desigualdad de cierre, intersección de círculos en cuadriláteros,
longitud de cada arista resultante y validación convexa compartida.
Rechaza entradas no finitas, degeneradas y fuera de precisión representable.
No sustituye algoritmos de rasterización ni introduce formatos backend.

`vertices_mm` permanece canónico en persistencia y consumo. Los ángulos se
derivan del resultado; la restricción elegida se conserva en el borrador del
editor, sin columnas nuevas. La escala uniforme del boceto sigue disponible
como opción explícita. Geometrías existentes sin esa configuración se abren
en modo de conservación del boceto para no cambiar su forma al editarlas.

## Pruebas ejecutadas

Desde `frontend`:

| Comando | Resultado final |
| --- | --- |
| `npm run test:unit` | 115 passed, 0 failed, 0 skipped. |
| `npm run test:component` | 219 passed, 0 failed; 23 archivos, 24,44 s. |
| `npm run lint` | Exit 0. |
| `npm run build` | Exit 0. Build local normal, no Staging. |
| `npm run test:e2e` | 40 descubiertos, 39 passed, 0 failed, 1 skipped; 43,5 s. Chrome local, proyectos chromium-desktop y chromium-mobile. |

En PowerShell se usó `npm.cmd`. E2E antepone `backend/venv/Scripts` al PATH
(Python 3.11); `PYTHON_DOTENV_DISABLED=1`, `NEWGLASS_REQUIRE_POSTGRES=1` y
`PGCTLTIMEOUT=85`. El launcher crea PostgreSQL aislado y API en loopback.
El nuevo caso de integración guarda tres piezas en un POST, lee el pedido
persistido mediante GET y compara lados y ángulo, sin mock de API/BD.

Único skip, preexistente y sin alteración: HU-014, proyecto chromium-mobile,
«Almacenero registra una baja y consulta el movimiento persistido».
Motivo literal: «La mutación agota un recurso compartido entre viewports.»
El caso se ejecuta en desktop. No se cuenta como passed.

Desde `backend`:

```powershell
$env:PYTHON_DOTENV_DISABLED='1'
.\venv\Scripts\python.exe -m pytest tests/unit/inventory/test_geometry.py tests/unit/modules/orders/domain/test_domain_geometry.py -q
```

Resultado: **190 passed en 0,20 s**. No se modificó backend ni migraciones;
no se vuelve a atribuir a estos cambios el resultado histórico de 1330 tests.

Delta respecto a 103 unitarias / 211 componentes / 32 E2E: +12 unitarias
(constructor geométrico), +8 componentes (5 editor, 1 retazo, 2 navegación),
+8 ejecuciones E2E (4 casos nuevos × 2 viewports). Ninguna prueba eliminada.
Las pruebas previas de escala/contorno ahora seleccionan explícitamente ese
modo conservado. Una prueba inicial de NuevoPedido falló por usar el nuevo
modo cíclico para probar rechazo de un boceto cóncavo; se corrigió su selección
de modo, manteniendo íntegra la aserción de rechazo y volviendo a ejecutar
toda la suite de componentes con éxito.

## Alcance y revisión

Producción modificada: `App.jsx`, `Sidebar.jsx`, `ui.css`, nuevo
`NavigationContext.js`, `CustomPieceEditor.jsx`/`.css` y nuevo
`constrainedGeometry.js`. No hay otro editor de retazos ni cambios de API.
Los módulos aún sin implementación no se presentan como botones ficticios.

SPEC §6.1 y §18 registran expresamente esta solicitud; no se reescriben
resultados históricos ni se altera CA-09 para hacerlo pasar. Estado formal
**Draft**, reviewer pendiente. La revisión técnica anterior corresponde a su
SHA, no a estos cambios posteriores. Permanece pendiente revisión humana.

Sin push, PR, merge, rebase, nuevos worktrees ni despliegue. No se utiliza
Supabase, Heroku, Pages ni servicios externos. Cambios conservados localmente
sin commit; logs transitorios retirados. `git diff --check` sin errores.
