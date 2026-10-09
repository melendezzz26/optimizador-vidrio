# Plan técnico de convergencia HU-006

Estado: implementación parcial; contrato multimaterial acordado, migración pendiente.

1. Conservar historia: merge no-ff de HU-006 desde main; no reescribir 80a4fa4.
2. Una pantalla en features/orders: estándares HU-006 + editor HU-007, material,
   espesor y cantidad por pieza, catálogo real, ordersApi y VITE_API_URL.
3. Mantener App/permisos y pages como compatibilidad temporal. Sin BrowserRouter obligatorio.
4. Restringir temporalmente guardado a una única pareja comprobada entre todas las piezas;
   no enviar multimaterial al backend antiguo ni tomar material de piezas[0].
5. Dependencias HTTP en Presentation con repositorio importado de forma diferida.
6. Implementar posteriormente el [contrato objetivo](contrato-orders.md) y el
   [plan BD](../../database/convergencia-orders-multimaterial.md) en componentes canónicos.
7. Concretar recuperación CA-02 y reautenticación sin pérdida antes de implementarlas.
8. Adaptar pruebas existentes: lista mixta, restricción temporal y validaciones nuevas
   ahora; persistencia multimaterial/migración después. No duplicar geometría o permisos.
9. Regresión global y evidencia antes de Verified; después rasterización Sprint 1.
   FF/BF/WF, métricas de colocación y selección de heurísticas: Sprint 2.
