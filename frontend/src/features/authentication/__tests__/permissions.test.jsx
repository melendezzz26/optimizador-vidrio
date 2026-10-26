import { expect, test } from 'vitest';
import {
  canExecuteOptimization, canManageOrders, canManagePlanchas, canManageRoles, canManageUsers,
  canViewAdministration, canViewDashboard, canViewInventory, canViewRoles, canViewUsers, hasPermission,
} from '../permissions';
import { withPermissions } from './permissionFixtures';

const MODULE_HELPERS = [
  canExecuteOptimization, canManageOrders, canManagePlanchas, canManageRoles, canManageUsers,
  canViewAdministration, canViewInventory, canViewRoles, canViewUsers,
];

test('las opciones dependen de los permisos recibidos y no del nombre del rol (CA-10)', () => {
  const adminWithoutPermissions = { rol: 'Administrador', permisos: [] };
  for (const helper of MODULE_HELPERS) expect(helper(adminWithoutPermissions)).toBe(false);
  expect(canViewAdministration({ rol: 'Almacenero', permisos: ['roles.view'] })).toBe(true);
});

test.each([null, undefined, {}, { rol: 'Administrador' }, { permisos: 'users.view' }])(
  'sin una lista de permisos válida no se ofrece nada (%j)',
  (user) => {
    for (const helper of MODULE_HELPERS) expect(helper(user)).toBe(false);
  },
);

test('Inicio (canViewDashboard) está disponible para cualquier usuario con sesión válida (HU-016 CA-01)', () => {
  expect(canViewDashboard(null)).toBe(false);
  expect(canViewDashboard(undefined)).toBe(false);
  expect(canViewDashboard({ rol: 'Administrador', permisos: [] })).toBe(true);
  expect(canViewDashboard({ rol: 'Operario', permisos: [] })).toBe(true);
  expect(canViewDashboard({ rol: 'Almacenero', permisos: [] })).toBe(true);
  expect(canViewDashboard({ username: 'O70000001' })).toBe(true);
});

test('cada helper consulta su permiso del catálogo', () => {
  const user = { permisos: ['inventory.view', 'orders.view', 'optimization.execute', 'users.view'] };
  expect(hasPermission(user, 'inventory.view')).toBe(true);
  expect(canViewInventory(user)).toBe(true);
  expect(canManagePlanchas(user)).toBe(false);
  expect(canManageOrders(user)).toBe(true);
  expect(canExecuteOptimization(user)).toBe(true);
  expect(canViewUsers(user)).toBe(true);
  expect(canManageUsers(user)).toBe(false);
  expect(canViewRoles(user)).toBe(false);
  expect(canViewAdministration(user)).toBe(true);
});

test.each([
  ['Administrador', true],
  ['Almacenero', false],
  ['Operario', false],
])('con la asignación inicial, %s ve Administración: %s', (rol, expected) => {
  expect(canViewAdministration(withPermissions({ rol }))).toBe(expected);
});