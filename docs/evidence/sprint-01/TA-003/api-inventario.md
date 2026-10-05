# Implementación de Capa Presentation (FastAPI) - TA-003

## Objetivo
El objetivo de esta iteración fue completar la capa de Presentación para el dominio de Inventario (TA-003) exponiendo los puertos de aplicación a través de endpoints REST en FastAPI.

## Endpoints Implementados
* **Tipos de Vidrio:**
  * `POST /api/inventory/tipos-vidrio`: Crea un tipo de vidrio. (201 Created)
  * `GET /api/inventory/tipos-vidrio`: Lista tipos de vidrio. (200 OK)
* **Planchas:**
  * `POST /api/inventory/planchas`: Crea una plancha. (201 Created)
  * `GET /api/inventory/planchas`: Lista planchas. (200 OK)
  * `PATCH /api/inventory/planchas/{id_plancha}`: Modifica una plancha parcialmente. (200 OK)
* **Retazos:**
  * `POST /api/inventory/retazos`: Crea un retazo con geometría estricta. (201 Created)
  * `GET /api/inventory/retazos`: Lista retazos. (200 OK)
  * `PATCH /api/inventory/retazos/{id_retazo}`: Modifica un retazo parcialmente. (200 OK)

## Esquemas Pydantic y Geometría
Se establecieron configuraciones estrictas (`extra="forbid"`) en los esquemas. Para el `POLIGONO_CONVEXO`, se aseguró que el arreglo contenga un mínimo de 3 vértices y que cada vértice sea una tupla exacta de dos elementos coordenados (`[x, y]`), ambos representados en `Decimal`.

## Errores (422) y Mapeo
Todos los mapeos a 422 utilizan la constante estandarizada `status.HTTP_422_UNPROCESSABLE_CONTENT`, eliminando dependencias obsoletas (`StarletteDeprecationWarning`) del framework.

## Aislamiento de Pruebas
Las pruebas de la API fueron aisladas limpiamente inyectando el `FakeInventoryService` a través de un *fixture* en Pytest que gestiona dinámicamente las overrides de dependencia, asegurando la no propagación de estado a las demás suites de la solución.

## Resultados
Al incorporar toda la cobertura para la API de Inventario, la suite total del repositorio fue promovida a **505 pruebas**, todas pasando existosamente (verde) y sin emitir advertencias de deprecación.
