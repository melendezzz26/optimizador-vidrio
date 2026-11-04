# PLAN TA-046 — Ajustes UX de registro y revisión

Responsable original: Fabricio Danniel Aguilar Chavez. Correcciones de cierre: Andro Joseph Quispe Cesias.
Revisor esperado: Andro Joseph Quispe Cesias; esta referencia no implica aprobación formal en GitHub.

1. **T01:** validar Enter, secuencia de foco, eliminación, importación y creación de polígonos con teclado sin alterar los flujos existentes.
2. **T02:** mostrar medidas originales del pedido tanto en comparación como en resultados individuales. Conservar precisión para rectángulos y círculos; redondear a 0,1 mm solo lados calculados de polígonos. La tabla es informativa y no participa en el cálculo ni la confirmación.
3. **T03:** ejecutar pruebas de unidad y componentes, lint y build; revisar HU-018 y el E2E de teclado en escritorio y móvil. Usar CI para E2E si no existe PostgreSQL local aislado.
4. Revisar el diff, publicar los cambios en la rama del PR y comprobar CI sobre el nuevo HEAD antes de considerar el merge.
