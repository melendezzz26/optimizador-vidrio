# Convergencia del modelo de datos a v1.1

## Línea base normativa

El documento aprobado `Documento_Diseno_Base_Datos_NewGlass_v1_1.docx` define
el modelo objetivo: 12 entidades y 90 columnas. OPTIMIZACION tiene 9 columnas,
incluida `criterio_seleccion_version VARCHAR(20) NOT NULL`; `LEX-V1` es la
versión inicial del criterio de selección, sin añadir un default de BD.

## Estado remoto observado previamente

La inspección anterior, realizada en modo solo lectura, observó una única fila
en `public.alembic_version`: `c4e8a1f2b3d5`. Las columnas y PK/FK/UNIQUE
comparadas coincidían con el resultado esperado de las migraciones de HU-003.
Este registro describe aquella inspección; no se volvió a consultar Supabase
durante la recuperación del historial.

## Recuperación de la historia en Git

El main de partida contenía únicamente `9b9f04eb67f6`. Se recuperó desde
`origin/feature/HU-003-gestion-usuarios` el archivo
[`c4e8a1f2b3d5_hu003_agregar_dni_y_usuario.py`](../../backend/alembic/versions/c4e8a1f2b3d5_hu003_agregar_dni_y_usuario.py),
sin cambios de contenido y conservando:

```text
revision = c4e8a1f2b3d5
down_revision = 9b9f04eb67f6
```

La recuperación restaura la correspondencia entre la historia disponible en
Git y el esquema remoto observado. No crea una migración equivalente ni duplica
la incorporación de DNI/usuario. No se hizo cherry-pick del commit completo
`809a2b7` ni se incorporaron su CRUD, frontend o imports funcionales.

La migración no se vuelve a ejecutar sobre Supabase: su revisión ya estaba
registrada y sus cambios estructurales estaban presentes en la inspección.

## Validación local

Desde `backend/`, usando el Python del entorno virtual en PowerShell:

```powershell
& ./venv/Scripts/python.exe -B -m alembic history
& ./venv/Scripts/python.exe -B -m alembic heads
```

Salida de `alembic history` (código 0):

```text
9b9f04eb67f6 -> c4e8a1f2b3d5 (head), HU-003: agregar dni y usuario a usuarios; correo pasa a opcional
<base> -> 9b9f04eb67f6, crear esquema inicial
```

Salida de `alembic heads` (código 0):

```text
c4e8a1f2b3d5 (head)
```

Existe un único head local. Estos comandos, con la configuración y opciones
utilizadas, leen los scripts locales sin ejecutar `env.py` ni conectarse a la BD.
No se ejecutaron `current`, `upgrade`, `downgrade`, `stamp` ni `revision`.

## Continuidad hacia v1.1

La primera nueva revisión v1.1 tendrá `down_revision = c4e8a1f2b3d5`.
Las siguientes continuarán esa cadena; todas descenderán de la revisión
recuperada. No se repetirán sus operaciones sobre DNI/usuario.

Esta fase no modifica `models.py`, no elimina correo, no añade fecha de creación
ni crea OPTIMIZACION o MATERIAL_UTILIZADO. El ORM aún conserva el estado anterior
a HU-003; restaurar el historial no equivale a alinear su metadata con el remoto
o con v1.1. Antes de generar futuras migraciones deberá alinearse el modelo
con la línea base y revisarse explícitamente la transformación de datos.

Se conserva una limitación histórica de `c4e8a1f2b3d5`: su `upgrade()` aborta
si `usuarios` contiene cualquier registro. Completar DNI no evita esa condición.
Esto debe contemplarse al probar otros entornos que todavía estén en la revisión
inicial; no justifica borrar usuarios, repetir la migración remota ni alterar
la revisión registrada para eludirla.

Los consumidores de correo y los imports antiguos de HU-003 se adaptarán en
fases posteriores coordinadas. No hubo conexiones ni modificaciones de datos
remotos durante esta fase.
