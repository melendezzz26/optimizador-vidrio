import { describe, expect, it } from 'vitest';
import { EMPTY_USER_FILTERS, filterUsers, hasActiveFilters } from '../userFilters';

const carlos = { usuario: 'F70303030', nombres: 'Carlos', apellidos: 'Pérez', id_rol: 3, estado: true };
const ana = { usuario: 'A00000001', nombres: 'Ana María', apellidos: 'Núñez', id_rol: 2, estado: false };
const admin = { usuario: 'A74000010', nombres: 'Admin', apellidos: 'NewGlass', id_rol: 1, estado: true };
const users = [carlos, ana, admin];

function filterWith(changes) {
  return filterUsers(users, { ...EMPTY_USER_FILTERS, ...changes });
}

describe('filterUsers (HU-003 T04)', () => {
  it('sin filtros devuelve todos los usuarios', () => {
    expect(filterWith({})).toEqual(users);
  });

  it('busca por una parte del usuario de acceso', () => {
    expect(filterWith({ query: '7030' })).toEqual([carlos]);
  });

  it('busca sin importar tildes ni mayúsculas', () => {
    expect(filterWith({ query: 'PEREZ' })).toEqual([carlos]);
    expect(filterWith({ query: 'nunez' })).toEqual([ana]);
  });

  it('acepta varias palabras en cualquier orden', () => {
    expect(filterWith({ query: '  pérez   carlos ' })).toEqual([carlos]);
  });

  it('filtra por rol', () => {
    expect(filterWith({ roleId: '2' })).toEqual([ana]);
  });

  it('filtra por estado', () => {
    expect(filterWith({ status: 'inactive' })).toEqual([ana]);
    expect(filterWith({ status: 'active' })).toEqual([carlos, admin]);
  });

  it('combina búsqueda, rol y estado; sin coincidencias devuelve una lista vacía', () => {
    expect(filterWith({ query: 'carlos', roleId: '3', status: 'active' })).toEqual([carlos]);
    expect(filterWith({ query: 'carlos', roleId: '3', status: 'inactive' })).toEqual([]);
  });
});

describe('hasActiveFilters', () => {
  it('no cuenta los espacios en blanco como búsqueda', () => {
    expect(hasActiveFilters(EMPTY_USER_FILTERS)).toBe(false);
    expect(hasActiveFilters({ ...EMPTY_USER_FILTERS, query: '   ' })).toBe(false);
    expect(hasActiveFilters({ ...EMPTY_USER_FILTERS, roleId: '1' })).toBe(true);
  });
});