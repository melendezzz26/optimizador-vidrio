# Plan de mejoras frontend — Optimización S1

Fecha: 2026-10-17. Estado: **Propuesto, sin implementación**.
Base: `2b21562`; rama obligatoria `feature/S1-optimization-ux-audit`.
Fuente: [AUDIT](AUDIT-S1-OPTIMIZATION-UX.md). Ejecución: [TASKS](TASKS-S1-OPTIMIZATION-UX.md).

La instrucción vigente del usuario pide entregar auditoría y plan antes de
corregir. Este documento no autoriza por sí solo iniciar los cambios ni declara
aprobación de negocio. Preserva arquitectura, contratos y UI en español; código
nuevo en inglés. Sin PR, rebase ni merge hacia integration.

## A. Correcciones frontend propuestas

| Orden | Bloque / hallazgos | Cambio concreto | Criterios de aceptación | Regresión necesaria |
|---|---|---|---|---|
| 1 | Contexto asíncrono AU-03/04 | Invalidar recuperaciones al cambiar selección/preparación; vincular continuación de confirmación al ID capturado; deshabilitar todas las acciones incompatibles durante confirmación | Una recuperación antigua no reemplaza trabajo nuevo; ningún botón inicia otro trabajo mientras POST confirm no esté reconciliado; no se repite POST automáticamente | GET demorado + selección/preparación; dos GET fuera de orden; POST demorado + botones; desmontaje; error incierto y recuperación |
| 2 | Grupos vacíos AU-02 | Mantener selección de grupo fuera de la condición que requiere contenedor; empty contextual sin ocultar otros grupos | Primer/último grupo sin placements no impide inspeccionar grupos válidos en 2D/3D; cambiar a vacío y regresar funciona | Componente y navegador con SIN_SOLUCION multi-grupo, orden invertido, todos vacíos, llegada progresiva |
| 3 | Diagnóstico AU-06 | Conservar `unplaced_units` en estado/snapshot y mostrar identificadores y motivos canónicos | Toda unidad pendiente/no colocada aparece una vez; estado SIN_SOLUCION nunca ofrece confirmación; no se infiere causa adicional | Contratos running/failed/no_solution, varias cantidades/materiales y móvil |
| 4 | Flujo y feedback AU-01/05/07/09 | Informar efecto de HU-015 antes de su acción; eliminar derivación imposible desde resultado; nombrar cierre local; estado explícito del resumen y progreso | No se promete preview de una corrida que no contiene máscaras; cerrar vista no aparenta cancelar servidor; ID recuperable y trabajo visible; etapas no aparentan medidas inexistentes | Textos/estado por fase; cierre/reconsulta; permisos; lectores de pantalla |
| 5 | Resolución/inspección AU-05 | Conservar configuración real del DTO y mostrar mm/celda en resultado; explicar diferencia entre raster del cálculo y máscara disponible para inspección | Valor coincide con snapshot persistido; ausencia explícita; no se vuelve a rasterizar en JS ni se solicita `/start` | Decimal positivo, resultados recuperados, catálogo ausente y permisos view-only |
| 6 | Cámara AU-08 | Límite único ±90° usado por clamp, ARIA, Home/End y pointer | Teclado/mouse/touch respetan límites; reset y presets coherentes; placements byte a byte intactos | Unit proyección, componente pointer/teclado, E2E desktop/mobile, reduced motion |
| 7 | Claridad visual AU-10 | Una leyenda con pedido/pieza/unidad/giro y coordenadas; ajustes secundarios 3D agrupados | Menos duplicación sin perder precisión; acciones alcanzables y foco visible a 390 px | Comparación de captura y navegación teclado; no snapshots masivos de markup |

No ampliar este bloque para implementar un motor frontend, generar máscaras
alternativas, cambiar agrupaciones canónicas, elegir stock no soportado o
modificar estados de pedidos desde la UI. La grilla 2D opcional debe describir
resolución real y nunca presentarse como validación de colisiones. El overlay de
contactos queda bloqueado por el contrato de máscaras descrito en B.

## B. Requiere backend

| Tema | Contrato pendiente | Por qué no es un arreglo frontend |
|---|---|---|
| AU-01: HU-015 y runs | Preview de geometrías/piezas de solo lectura o convergencia explícita del ciclo heredado | `/start` cambia estado y `/rasterize` exige EN_OPTIMIZACION; no basta renombrar botones |
| AU-05: inspección de corrida | Acceso autorizado a máscaras utilizadas, resolución/orientación/origen, identidad de corrida y contenedor; límites/paginación/presupuesto | El DTO actual no contiene las máscaras; recrearlas en cliente no garantiza equivalencia con el cálculo |
| AU-07: cancelar corrida | Si negocio lo requiere, transición transaccional y reglas de recuperación | No existe endpoint de cancelación; descartar localmente no revierte pedidos |

Probar estos contratos en entorno de pruebas preparado por el equipo. No instalar
PostgreSQL, crear BD o migrar para esta fase. No encubrir fallos backend con éxito
visual, métricas calculadas por aproximación o cambios manuales de estado.

## C. Decisiones de negocio

- Determinar si la herramienta heredada debe seguir iniciando pedidos o quedar
  solo como recuperación de procesos antiguos; definir salida de EN_OPTIMIZACION.
- Definir qué significa abandonar un corte persistido y quién puede liberar sus
  pedidos. Mantener distinguibles cerrar vista, descartar propuesta y cancelar.
- Confirmar origen editable de resolución y parámetros. Hoy el backend toma
  configuración persistida; el frontend no debe prometer parámetros por corrida
  que el POST no acepta.
- Identificar una cuenta/sesión y pedidos de staging inequívocamente de prueba
  para recorrer el flujo real. No usar cuentas del servidor E2E local en staging.

## D. Fuera de alcance

Reimplementación del motor; BF/WF; CAD/renderer WebGL; política de retazos;
migraciones; cambios de stock compartido; despliegue; instalar servicios globales;
PR/merge a integration. AU-11 puede resolverse en un bloque documental separado,
sin reescribir evidencias históricas ni afirmar validaciones no ejecutadas.

## Validación prevista

1. Antes de código: revisar Git y fetch. Si integration avanzó, inspeccionar e
   integrar con merge normal, nunca rebase, sin sobrescribir trabajo ajeno.
2. Reproducir cada caso AU-02/03/04 en una prueba que falle en la base y pase con
   el cambio; completar matrices de estado para las demás correcciones.
3. Ejecutar unit, component, lint y build usando Node portable y lockfile vigente.
4. Ejecutar navegador controlado desktop/mobile con observación de `pageerror`,
   consola y respuestas. Los fixtures validan interfaz, no motor/inventario.
5. E2E real solo cuando exista entorno autorizado ya preparado compatible con
   la restricción de no crear BD. El runner actual arranca una BD efímera; no
   lanzarlo sin revisar esa restricción. Staging requiere cuenta de prueba y
   datos identificados; no ejecutar cálculo/confirmación sobre datos reales.
6. Guardar evidencia antes/después enfocada por fallo, sin tokens, datos personales
   ni capturas redundantes; reportar por separado límites y pruebas no ejecutadas.

## Entrega por bloques

Commits coherentes de contexto asíncrono, grupos/diagnóstico, flujo/raster y
cámara/UX. Publicar feature aproximadamente cada 2–3 commits significativos y
revisar integration antes de bloques grandes. No publicar PR. Al cerrar, reportar
SHA base, cambios, pruebas reales, pendientes B/C, evidencia, commits/push y
`git status`. Esta fase solo publica documentos y evidencia de auditoría.
