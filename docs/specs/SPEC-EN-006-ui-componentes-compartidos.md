| **Campo** | **Valor**                                   |
|-----------|---------------------------------------------|
| Proyecto  | NewGlass — Optimizador de corte de vidrio   |
| Documento | SPEC-EN-006                                 |
| Versión   | 1.0                                         |
| Estado    | Draft                                       |
| Fecha     | 08/10/2026                                  |
| Alcance   | Sprint 1 — Base funcional pre-rasterización |

# 1. Objetivo

Establecer un patrón visual y de interacción común para los módulos de gestión antes de rasterización.

# 2. Patrón de gestión

| **Regla**              | **Aplicación**                                                                   |
|------------------------|----------------------------------------------------------------------------------|
| Listado primero        | Users, Inventory y Orders muestran gestión antes del formulario.                 |
| Formulario bajo acción | Nuevo/Editar abre formulario; Cancelar/Guardar retorna al listado.               |
| Feedback común         | Éxito, error, advertencia, información, loading, vacío, disabled y confirmación. |
| Acciones contextuales  | Evitar botones permanentes que generan ruido; usar menú/edición para bajas.      |
| Accesibilidad          | Labels visibles, foco, teclado, contraste y mensajes próximos al control.        |

# 3. Editor poligonal reutilizable

- Extraer la lógica de dibujo, cierre, segmentos, medidas, reconstrucción y convexidad desde HU-007.

- Orders lo abre solo cuando la forma es POLIGONO_CONVEXO y lo cierra al agregar/actualizar la pieza.

- Inventory lo reutiliza para registrar/editar retazos poligonales.

- El componente compartido no realiza HTTP ni conoce PEDIDO/RETAZO; devuelve geometría validada mediante props/callbacks.

# 4. Criterios de aceptación

| **CA** | **Criterio**                                                                                |
|--------|---------------------------------------------------------------------------------------------|
| CA-01  | No existen dos implementaciones distintas del editor poligonal.                             |
| CA-02  | Los tres módulos principales comparten estados/mensajes visuales.                           |
| CA-03  | No se muestran acciones ficticias sin flujo implementado.                                   |
| CA-04  | La UI mantiene el estilo azul, superficies claras/desenfocadas y comportamiento responsive. |
