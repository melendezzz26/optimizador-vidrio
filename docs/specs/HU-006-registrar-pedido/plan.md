# Plan Técnico: HU-006 Registrar Pedido

## 1. Frontend (React)
- **Refactorización de UI:** Eliminar el catálogo "hardcodeado" de vidrios y consumirlo desde el backend (`GET /api/inventory/tipos-vidrio`), cumpliendo la regla arquitectónica de no tener lógica de negocio en la vista.
- **Estado y Prevención:** Implementar estados `isLoading` para la carga inicial y `isSubmitting` para el guardado del pedido, deshabilitando el botón principal para evitar doble envío.
- **UI/UX:** Aumentar la opacidad del fondo de la tarjeta principal para reducir la competencia visual con la imagen fotográfica, y asegurar el foco de teclado en los selects y botones.

## 2. Backend (FastAPI - Módulo `orders`)
- **Presentation:** Crear el router `POST /api/orders` y los schemas de validación (Pydantic) para el payload entrante.
- **Application:** Implementar `RegistrarPedidoUseCase` que orqueste la validación de las piezas y la creación del pedido.
- **Domain:** Definir validaciones de negocio (espesores permitidos, cantidades > 0) independientes del framework.
- **Infrastructure:** Crear el repositorio SQLAlchemy que inserte en `PEDIDO` y `PIEZA` dentro de una transacción atómica.