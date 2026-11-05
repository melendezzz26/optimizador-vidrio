# TA-045 — Limpieza del commit documental no publicado

La rama candidata es `recovery/sprint-02`. Su estado inicial se comprobó limpio en
`0b759f6ce82516d08f9134ccea540b57f34a2549`, con padre productivo
`04fa083822f1b9e297092a9fa3507f9c8bbe3d08`. El HEAD remoto se verificó con
`git ls-remote`: `origin/recovery/sprint-02` sigue en
`2c592296f6ffcc2befc0fef0f05c1024f0d378d4`.

Se trabajó en el worktree que ya tenía `recovery/sprint-02`; el directorio desde el
que se abrió la sesión correspondía a otro worktree, en la rama fix. No se cambió
la rama de ese otro worktree ni se modificaron main o ramas de integración.

## Respaldo anterior a cualquier eliminación

- Referencia conservada: `refs/heads/backup/TA-045-e2e-before-zip-exclusion-0b759f6`.
- Commit de respaldo: `0b759f6ce82516d08f9134ccea540b57f34a2549`.
- Archivo externo: `artifacts.zip`, 54,650,696 bytes.
- SHA-256 externo: `5b49c09234f6377e5f1e1d41ab92c911f5fcb5a6f25de7df04d0bbb03553f92a`.
- Blob Git original: `3f4a2ad95ac5e58749daa1cd37dd114a96f2e717`.
- Raíz externa lógica: `newglass-evidence-backups/TA-045/0b759f6ce82516d08f9134ccea540b57f34a2549/`.
- Bajo esa raíz se conserva `docs/evidence/sprint-02/TA-045/global-e2e/run-01/artifacts.zip`.

El directorio externo se comprobó fuera de todos los worktrees y sin ancestro
Git. Primero se copió el archivo, luego se verificaron tamaño y SHA-256 y solo
entonces se retiró del candidato. El respaldo y su referencia no se eliminaron.
La referencia de respaldo y la rama fix conservan localmente el historial original;
no forman parte de los objetos alcanzables desde la rama candidata reconstruida.

## Revisión de datos

Se revisaron los **27 archivos textuales** de las evidencias TA-045 originales,
incluidos **11 JSON**, excluyendo el ZIP completo que queda externo. Se buscaron
claves privadas, tokens JWT/proveedores/GitHub/AWS, contraseñas en URI, endpoints
Supabase, correos y campos JSON de contraseña, autorización, claves, DNI y contacto.
No se hallaron valores de credenciales, secretos ni datos personales en esos campos.
El detalle y los hashes del material original revisado están en `privacy-review.json`.

La revisión manual adicional de los manifiestos y logs confirma que se describen
configuración, resultados de pruebas, rutas de diagnóstico e identificadores
sintéticos; `r1_test` no tiene contraseña publicada y solo se registran las dos
bases efímeras de loopback ya detenidas. No se incorpora un volcado de datos ni el
contenido del ZIP al commit reconstruido. Los nuevos descriptores externos usan
una ruta lógica portátil, sin publicar la ubicación absoluta del respaldo.

## Reconstrucción y alcance

Se reemplazó únicamente el último commit documental no publicado mediante amend,
manteniendo su padre **04fa083**. No se añadió un commit de borrado encima de
0b759f6, porque eso conservaría el ZIP como ancestro publicable.

No se utilizó `git reset --hard`, force push ni limpieza de objetos. No se tocaron
algoritmos, pruebas, workflows, contratos de cobertura ni límites. El árbol completo
de 04fa083 sigue siendo `c36b20b07259e55325e5ac3d71bafdcb39a3a50f`.

El paquete versionado conserva sus 15 evidencias ligeras originales sin cambios
de bytes, más `external-artifacts.json` y `EXTERNAL-SHA256SUMS`. `SHA256SUMS` comprueba
solo esos 17 archivos presentes en un clon limpio. La integridad del ZIP se comprueba
separadamente contra el respaldo externo. El inventario de 623 artefactos describe
ese ZIP, no archivos que deban existir dentro del clon.

La certificación conserva **146/146 PASS** (B02 1+1, resto 72+72), UUID
`82919e96-75f1-4625-8694-a64e6d090fb6` y digest lógico
`9a1e20d8eb9767f4e399f5bfc65e613d5d597f5b565d73cb138c712e2fb4c18b`.
No se repitió el backend ni Playwright: solo cambian documentación y ubicación del
archivo externo. Sí se verifican de nuevo manifiestos, gate e historial candidato.

## Verificaciones del candidato

Desde la raíz de la rama `recovery/sprint-02`:

```bash
git status --short --branch
git rev-parse HEAD^ 04fa083^{tree}
git rev-parse refs/heads/backup/TA-045-e2e-before-zip-exclusion-0b759f6
git log --oneline origin/recovery/sprint-02..HEAD
git merge-base --is-ancestor origin/recovery/sprint-02 HEAD
git diff --exit-code 04fa083 HEAD -- backend frontend .github
git diff --check HEAD^ HEAD
git rev-list --objects HEAD | grep '^3f4a2ad95ac5e58749daa1cd37dd114a96f2e717\( \|$\)'
git rev-list HEAD | grep '^0b759f6ce82516d08f9134ccea540b57f34a2549$'
git rev-list --objects origin/recovery/sprint-02..HEAD |
  git cat-file --batch-check='%(objectname) %(objecttype) %(objectsize) %(rest)'
```

Los dos `grep` deben devolver **sin coincidencias** (exit 1): el ZIP y el commit
documental anterior no son alcanzables desde HEAD. El primer padre es 04fa083 y la
lista desde origin contiene solo la corrección productiva y el nuevo documental.
La prueba de ascendencia debe terminar en exit 0: el avance desde origin es fast-forward.
El tamaño de los blobs nuevos se inspecciona con el último comando; el ZIP no aparece.

La auditoría del rango nuevo encontró **37 blobs**, con un máximo de **167,844 bytes**
(`artifact-inventory.json`); ningún blob nuevo alcanza 1 MiB. El objeto ZIP no aparece
en todo el recorrido de objetos alcanzables de la candidata, y 0b759f6 no es ancestro.
Ambos siguen disponibles en la referencia local de respaldo, tal como se requiere.

También se materializaron las 17 evidencias ligeras y los módulos del gate desde el
índice en directorios vacíos, con `core.autocrlf=true` y `core.autocrlf=false`.
En ambos casos coincidieron los 17 hashes y pasó el gate 146/146 sin existir ZIP.
`EXTERNAL-SHA256SUMS` tiene una regla LF explícita para mantener esa propiedad en Windows.

Para los hashes y el gate, seguir [las instrucciones del informe global](../README.md).
No usar `--all` al comprobar la exclusión: deliberadamente existe un respaldo local
que conserva el objeto original, y no se ha eliminado. No se hizo push, actualización
del PR #102, cambios en Supabase ni despliegue.
