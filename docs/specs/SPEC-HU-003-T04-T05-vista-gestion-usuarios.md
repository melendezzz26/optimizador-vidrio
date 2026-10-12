# SPEC-HU-003-T04-T05 — Vista de gestión de usuarios

| Campo | Valor |
|---|---|
| Estado | Reviewed |
| PBI relacionado | HU-003 T04 y T05 · depende de TA-034 (EN-006) |
| Responsable | Fabricio A. |
| Origen | SPEC_HU-003_Mejora_Gestion_Usuarios v1.0 (08/10/2026), aprobada en el refinamiento pre-raster |

## 1. Objetivo

Mantener el CRUD existente, pero convertir la experiencia en una vista de gestión consistente con Inventory y Orders.

## 2. Pantalla

| Elemento | Regla |
|---|---|
| Listado | Es la vista inicial del módulo. |
| Búsqueda | Busca por usuario, nombres/apellidos u otro identificador ya expuesto por la API. |
| Filtro Rol | Administrador / Almacenero / Operario / Todos. |
| Filtro Estado | Activo / Inactivo / Todos. |
| Nuevo usuario | Abre el formulario de alta bajo acción. |
| Editar | Abre el formulario con datos actuales. |

## 3. Criterios de aceptación

| CA | Criterio |
|---|---|
| CA-01 | El formulario de alta no se muestra permanentemente al entrar al módulo. |
| CA-02 | Búsqueda y filtros pueden combinarse y muestran estado vacío cuando no hay coincidencias. |
| CA-03 | Los mensajes de validación usan el sistema de feedback compartido. |
| CA-04 | Las restricciones por rol siguen aplicándose en backend y UI. |

## 4. Pruebas

- Componente de búsqueda/filtros.
- Alta y edición.
- Usuario duplicado.
- Activar/desactivar.
- Permisos Administrador.

## 5. Impacto técnico (propuesta a revisar en el PR)

- **Módulo:** solo frontend, `frontend/src/features/users/`. Sin cambios de API ni de BD (no hay migración Alembic).
- **Filtrado en el cliente:** `GET /api/users` ya devuelve todos los usuarios y el volumen es pequeño (personal de un taller). Filtrar en el navegador evita cambiar el contrato de la API. Si el volumen crece, se evaluará paginación y filtros en el backend.
- **Búsqueda:** por usuario de acceso, nombres y apellidos, sin distinguir tildes ni mayúsculas. El DNI no se muestra en la tabla (RN-09 de SPEC-HU-003), pero forma parte del usuario de acceso, así que también se encuentra por esos dígitos.
- **Permisos:** no cambian. La API sigue restringida al Administrador (`require_permission`) y la pantalla solo se muestra a ese rol.
- **Patrón:** `useManagementView` de TA-034 T02 para "listado primero, formulario bajo acción".