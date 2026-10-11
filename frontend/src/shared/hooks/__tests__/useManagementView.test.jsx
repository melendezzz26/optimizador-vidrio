import { act, renderHook } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { useManagementView } from '../useManagementView';

describe('useManagementView', () => {
  it('empieza mostrando el listado, sin formulario', () => {
    const { result } = renderHook(() => useManagementView());
    expect(result.current.mode).toBe('list');
    expect(result.current.isListVisible).toBe(true);
    expect(result.current.isFormOpen).toBe(false);
  });

  it('abre el formulario de alta solo con la acción Nuevo', () => {
    const { result } = renderHook(() => useManagementView());
    act(() => result.current.openCreate());
    expect(result.current.mode).toBe('create');
    expect(result.current.isListVisible).toBe(false);
    expect(result.current.editingItem).toBeNull();
  });

  it('abre la edición con el registro elegido', () => {
    const { result } = renderHook(() => useManagementView());
    const carlos = { id_usuario: 2, usuario: 'F70303030' };
    act(() => result.current.openEdit(carlos));
    expect(result.current.mode).toBe('edit');
    expect(result.current.editingItem).toBe(carlos);
  });

  it('al guardar vuelve al listado y conserva el mensaje de resultado', () => {
    const { result } = renderHook(() => useManagementView());
    act(() => result.current.openCreate());
    act(() => result.current.backToList({ variant: 'success', message: 'Usuario creado.' }));
    expect(result.current.mode).toBe('list');
    expect(result.current.feedback).toEqual({ variant: 'success', message: 'Usuario creado.' });
  });

  it('al cancelar vuelve al listado sin mensaje', () => {
    const { result } = renderHook(() => useManagementView());
    act(() => result.current.openCreate());
    act(() => result.current.backToList());
    expect(result.current.mode).toBe('list');
    expect(result.current.feedback).toBeNull();
  });

  it('una nueva acción limpia el mensaje anterior', () => {
    const { result } = renderHook(() => useManagementView());
    act(() => result.current.backToList({ variant: 'success', message: 'Usuario creado.' }));
    act(() => result.current.openEdit({ id_usuario: 2 }));
    expect(result.current.feedback).toBeNull();
  });
});