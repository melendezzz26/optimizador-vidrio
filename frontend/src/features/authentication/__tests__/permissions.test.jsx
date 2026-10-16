import { expect, test } from 'vitest';
import {
  canExecuteOptimization, canManageOrders, canManagePlanchas, canManageRoles, canManageUsers,
  canViewAdministration, canViewDashboard, canViewInventory, canViewRoles, canViewUsers, hasPermission,
} from '../permissions';
import { withPermissions } from './permissionFixtures';

const ALL_HELPERS = [
  canExecuteOptimization, canManageOrders, canManagePlanchas, canManageRoles, canManageUsers,
  canViewAdministration, canViewDashboard, canViewInventory, canViewRoles, canViewUsers,
];

test('las opciones dependen de los permisos recibidos y no del nombre del rol (CA-10)', () => {
  const adminWithoutPermissions = { rol: 'Administrador', permisos: [] };
  for (const helper of ALL_HELPERS) expect(helper(adminWithoutPermissions)).toBe(false);
  expect(canViewAdministration({ rol: 'Almacenero', permisos: ['roles.view'] })).toBe(true);
});

test.each([null, undefined, {}, { rol: 'Administrador' }, { permisos: 'users.view' }])(
  'sin una lista de permisos válida no se ofrece nada (%j)',
  (user) => {
    for (const helper of ALL_HELPERS) expect(helper(user)).toBe(false);
  },
);

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