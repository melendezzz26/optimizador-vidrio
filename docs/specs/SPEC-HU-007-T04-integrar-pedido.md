# SPEC — HU-007 T04: Integrar pieza personalizada con registro persistente de pedido

## Información general

| Campo | Valor |
|---|---|
| Estado | Reviewed |
| PBI relacionado | HU-007 |
| Tarea | T04 — Integrar pieza personalizada con registro de pedido |
| Responsable | Andro Joseph Quispe Cesias |
| Reviewer propuesto | Luis Anthony Ibañez Herrera |
| Dependencia | T03 — Validar polígono convexo |
| Rama | feature/HU-007-lienzo-pieza-personalizada |
| Motivo | HU-006 es la dependencia funcional directa del módulo Orders y su responsable debe revisar que T04 no contradiga el contrato de Registrar pedido. |

---

## 1. Objetivo

Integrar la pieza personalizada validada por T03 con el flujo real de registro de pedido en la base de datos PostgreSQL, empleando Clean Architecture y manteniendo las responsabilidades estrictas entre las capas.

---

## 2. Alcance

### Incluye
- Conectar el componente de la pieza personalizada (CustomPieceEditor) con el formulario principal del pedido.
- Habilitar la agregación de múltiples piezas locales antes de guardarlas definitivamente en la base de datos.
- Reutilizar el contrato funcional de POST /api/orders.
- Reutilizar modelos SQLAlchemy canónicos Pedido y Pieza.
- Integrar la autenticación real por JWT de origin/main.
- Persistir pedido y piezas de forma transaccional.
- Validar las reglas del catálogo en el backend (tipos de vidrio y espesor).
- Prevenir envío doble desde el frontend.

### Fuera de alcance
- Rediseño visual general de NuevoPedido.
- Modificación de esquemas de base de datos o migraciones de Alembic (se usa el HEAD actual 1c8754481a08).
- Creación de modelos SQLAlchemy duplicados o tablas auxiliares.
- Uso de simulaciones (mocks) para la autenticación de usuarios en el backend.
- Lógica compleja de idempotencia de doble submit en base de datos.
- Pruebas automatizadas en Cypress o scripts de Python paralelos.

---

## 3. Precondiciones

- Las fases **T01**, **T02** y **T03** deben estar operativas y sus 132 pruebas automatizadas deben ejecutarse exitosamente.
- La rama debe estar sincronizada con origin/main incluyendo el sistema de autenticación real y los catálogos base.
- Se reutilizarán estrictamente las tablas pedidos y piezas ya declaradas y mapeadas en ackend/app/models.py.

---

## 4. Flujo de Interacción

1. El Operario selecciona tipo de vidrio y espesor en la UI.
2. Dibuja el polígono interactivo.
3. Ingresa las dimensiones reales de los segmentos.
4. T03 de frontend valida la geometría automáticamente y devuelve VALID.
5. El botón "Agregar pieza al pedido" se habilita únicamente cuando:
   - La geometría está cerrada.
   - Todas las medidas necesarias son válidas y coherentes.
   - Existe ertices_mm de forma completa.
   - T03 retorna expresamente VALID.
   - Los datos requeridos del encabezado del pedido están seleccionados.
6. Al presionar "Agregar pieza":
   - **NO** se escribe de inmediato en BD.
   - Se agrega la pieza al estado local de NuevoPedido.
   - Queda como pieza tipo POLIGONO_CONVEXO.
   - Cantidad inicial = 1.
   - Tras esto, el lienzo de dibujo debe reiniciarse para recibir nuevas figuras.
7. El usuario puede seguir agregando múltiples piezas al mismo pedido.
8. El botón principal "Guardar pedido" dispara un único POST /api/orders con todos los datos.
9. Durante la transacción asíncrona:
   - isSubmitting = true.
   - Los botones se deshabilitan en el UI.
   - Se imposibilita el doble clic / doble submit.
10. Si la API responde 201 Created:
    - Se confirma el éxito.
    - Se captura el id_pedido retornado.
    - Se verifica que el registro exista en BD.
11. Si la API falla:
    - Las piezas en el borrador de la vista local **NO** deben borrarse/perderse.
    - Se muestra mensaje de error accesible al usuario.
    - El operario puede corregir o reintentar la acción.

---

## 5. Contrato HTTP (API)

La API NO debe depender ni confiar de manera exclusiva en rea_mm2 o la geometría derivada en el frontend; se envían los datos base y el backend los consolida y valida independientemente.

**TRANSPORTE HTTP DESDE FRONTEND:**

Para formas regulares, se envían las dimensiones. Para POLIGONO_CONVEXO, el frontend **NO** envía rea_mm2, ni geometria, ni dimensiones=null como dato requerido. Solo envía los ertices_mm.

Contrato de entrada sugerido (JSON Payload):
`json
{
  "id_tipo_vidrio": 1,
  "espesor_mm": 6,
  "piezas": [
    {
      "tipo_forma": "RECTANGULO",
      "cantidad": 1,
      "width_mm": 1000.0,
      "height_mm": 800.0
    },
    {
      "tipo_forma": "CIRCUNFERENCIA",
      "cantidad": 2,
      "radius_mm": 200.0
    },
    {
      "tipo_forma": "POLIGONO_CONVEXO",
      "cantidad": 1,
      "vertices_mm": [
        [0,0],
        [500,0],
        [500,300],
        [0,300]
      ]
    }
  ]
}
`
*Nota: Se recomienda el uso de esquemas discriminados (Union) en Pydantic por tipo de forma en la capa Presentation.*

---

## 6. Persistencia Canónica en PostgreSQL

El backend recibe los datos del transporte HTTP, vuelve a validar la geometría, y deriva la representación de persistencia.

Las representaciones en Base de Datos de dimensiones (opcional) y geometria (obligatoria JSONB) deben adherirse a las siguientes estructuras de representación física:

**RECTANGULO:**
- dimensiones = {"type": "RECTANGULO", "width_mm": W, "height_mm": H}
- geometria = {"type": "RECTANGULO", "width_mm": W, "height_mm": H}

**CIRCUNFERENCIA:**
- dimensiones = {"type": "CIRCUNFERENCIA", "radius_mm": R}
- geometria = {"type": "CIRCUNFERENCIA", "radius_mm": R}

**POLIGONO_CONVEXO:**
- dimensiones =
ull
- geometria = {"type": "POLIGONO_CONVEXO", "vertices_mm": [[...], [...], ...]}

*Aclaración: rea_mm2 será calculada exclusivamente por el backend en todos los casos.*
---

## 7. Validaciones Backend

- POLIGONO_CONVEXO requiere mínimo de 3 vértices.
- Coordenadas estrictamente numéricas finitas.
- Geometría no degenerada (colineales puros, autointersecciones o cruces).
- El polígono es estrictamente simple.
- El polígono debe ser convexo.
- Área total debe ser mayor a 0.
- La combinación solicitada (id_tipo_vidrio + espesor_mm) corresponde a una existente y válida en el catálogo.
- La cantidad de cada pieza debe ser estrictamente > 0.
- El estado del pedido persiste de forma implícita o explícita como PENDIENTE.

---

## 8. Arquitectura y Reglas

**Capa Backend (Clean Architecture):**
- **Domain:** Aislada de Frameworks. Aquí van los validadores geométricos de servidor y reglas de negocio puras. No existen imports a FastAPI, SQLAlchemy, ni esquemas (Pydantic) de Presentation.
- **Application:** Orquesta puertos de dominio. No importa NUNCA representaciones de Presentation (p.ej., Pydantic schemas) para pasar sus datos.
- **Infrastructure:** Instancia conectores y repositorios de BD que implementan puertos abstractos, importando los Modelos SQLAlchemy Canónicos de pp.models.
- **Presentation:** Expone el HTTP (FastAPI / Router) e inyecta dependencias al UseCase.

---

## 9. Seguridad (Auth)

Todo acceso para registrar pedidos exige las rutinas genuinas JWT establecidas en origin/main.
- Validar JWT mediante dependencia de ruta: get_current_user.
- Validar con: equire_permission(...) el acceso funcional necesario.
- Capturar siempre la ID del usuario registrado mediante la identidad devuelta en el token validado.

---

## 10. Transacción de BD

- La persistencia de la cabecera Pedido junto a sus hijos Piezas será totalmente atómica.
- En caso de un fallo procesando la cabecera, o de cualquier pieza individual en la iteración, se obligará un **rollback** absoluto de la sesión.

---

## 11. Errores HTTP Proyectados

- **401 Unauthorized:** Intento sin un Bearer Token válido.
- **403 Forbidden:** Intento con Token donde el usuario carece del rol necesario.
- **422 Unprocessable Entity:** Falla de esquema de entrada y/o validación de dominio geométrico.
- **500 Internal Server Error:** Falla subyacente (sin exponer stack traces).

---

## 12. Criterios de Aceptación (CA)

- **CA-T04-01:** Una geometría personalizada VALID puede añadirse a la lista local del pedido.
- **CA-T04-02:** Una geometría inválida o incompleta no puede añadirse a la lista.
- **CA-T04-03:** Agregar una pieza en UI no persiste transaccionalmente ni graba datos intermedios en DB.
- **CA-T04-04:** Guardar pedido envía un solo paquete consolidado por POST /api/orders.
- **CA-T04-05:** Backend efectúa una re-validación profunda sobre el objeto geométrico independientemente de cualquier estado VALID enviado por el Frontend.
- **CA-T04-06:** Pedido y sus piezas asociadas son insertados de manera Atómica a BD PostgreSQL.
- **CA-T04-07:** El usuario responsable de la inserción es identificado internamente extrayendo información del Token JWT.
- **CA-T04-08:** Todo espesor_mm y material es validado cruzando con su viabilidad contra catálogo vigente.
- **CA-T04-09:** Las fallas de la API en el guardado conservan el borrador íntegro del usuario en UI sin pérdidas.
- **CA-T04-10:** Activar el botón de guardar un pedido asume estado "loading" prohibiendo explícitamente re-ejecutar.
- **CA-T04-11:** Se respetan esquemas globales, excluyendo migración adicional u ocurrencia de dobles Modelos SQLAlchemy.
- **CA-T04-12:** Total de las 132 Pruebas Automatizadas de Frontend heredadas de fases pasadas ejecutan PASS continuo.

---

## 13. Estrategia de Pruebas

- **Backend:** Unitarias de Dominio (geometría y math), Unitarias API, Integración Infra (Test DB + atómico rollback).
- **Frontend:** Vitest para React states (loading boolean, validate triggers).
- **E2E:** Playwright (flujo interactivo UI Login -> T01 -> T02 -> T03 -> Agregar -> Guardar -> POST).

---

## 14. Archivos Previstos a Intervenir / Crear

**Nuevos (Backend Orders):**
- pp/modules/orders/domain/order.py
- pp/modules/orders/domain/geometry.py
- pp/modules/orders/application/ports.py
- pp/modules/orders/application/use_cases.py
- pp/modules/orders/infrastructure/repositories.py
- pp/modules/orders/infrastructure/dependencies.py
- pp/modules/orders/presentation/schemas.py
- pp/modules/orders/presentation/router.py

**Modificados:**
- ackend/main.py
- rontend/src/features/orders/CustomPieceEditor.jsx
- rontend/src/pages/NuevoPedido.jsx
- rontend/tests/e2e/hu007-custom-piece.spec.js
- Archivos test (Backend pytest / Frontend vitest).

---

## 15. Evidencias

Documentación con bitácora de evidencia alojada en docs/evidence/sprint-01/HU-007/ detallando comandos, pases de Tests, lint y build logs.

---

## 16. Definition of Done

- [ ] Código alojado e implementado sin regresiones.
- [ ] Mantiene modularidad, evitando solapamientos / duplos SQLAlchemy y fallos lógicos Architecture.
- [ ] Pasa todas las pruebas requeridas deben pasar en Pipelines (Backend Pytest, Frontend Vitest + Playwright E2E).
- [ ] Lint y format validan estrictamente limpio.
- [ ] Aprobación formal (Review) de Stakeholder y Reviewer Propuesto.
- [ ] Rama disponible para rebase o Integración definitiva sin conflictos destructivos de origin/main.
