import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, test, vi } from 'vitest';
import CustomPieceEditor from '../CustomPieceEditor';
import { edgeLengths, interiorAngles } from '../polygonMeasurements';
import { validateConvexPolygon } from '../convexityValidation';

const field = i => screen.getByLabelText(`Longitud del segmento S${i} en milímetros`);
const fill = values => values.forEach((value, i) => fireEvent.change(field(i + 1), { target: { value: String(value) } }));

test('actualiza medidas parciales, conserva el boceto y nunca publica una geometría estimada', async () => {
  const user = userEvent.setup(); const changed = vi.fn();
  render(<CustomPieceEditor onGeometryChange={changed} />);
  expect(screen.getByText('Dibuja la forma aproximada de la pieza. Luego ajusta sus medidas y ángulos para definirla con precisión.')).toBeVisible();
  await draw(user, 4);
  const svg = screen.getByRole('img', { name: 'Vista dimensional de la pieza' });
  const points = () => svg.querySelector('polygon').getAttribute('points');
  const reference = svg.querySelector('.custom-piece-editor__sketch-reference').getAttribute('points');
  fireEvent.change(field(1), { target: { value: '300' } });
  expect(svg).toHaveTextContent('S1 · 300 mm');
  expect(svg.querySelectorAll('line[data-measured="true"]')).toHaveLength(1);
  const first = points();
  fireEvent.change(field(2), { target: { value: '150' } });
  expect(points()).not.toBe(first);
  expect(svg.querySelector('.custom-piece-editor__sketch-reference')).toHaveAttribute('points', reference);
  expect(svg.querySelector('polygon')).toHaveAttribute('data-provisional', 'true');
  expect(field(3)).toHaveValue(null);
  expect(changed.mock.calls.at(-1)[0]).toBeNull();
  expect(screen.getByRole('status', { name: 'Resultado de validación geométrica' })).toHaveTextContent('2 de 4 medidas');
  fill([300, 150, 300, 150]);
  expect(changed.mock.calls.at(-1)[0]).not.toBeNull();
  expect(svg.querySelector('.custom-piece-editor__sketch-reference')).toBeNull();
  fireEvent.change(field(2), { target: { value: '' } });
  expect(changed.mock.calls.at(-1)[0]).toBeNull();
  expect(svg.querySelector('polygon')).toHaveAttribute('data-provisional', 'true');
});
async function draw(user, count) {
  const points = Array.from({ length: count }, (_, i) => [350 + 150 * Math.cos(i * 2 * Math.PI / count), 250 + 150 * Math.sin(i * 2 * Math.PI / count)]);
  for (const [x, y] of points) await user.pointer({ target: screen.getByRole('img', { name: /Lienzo del dibujo original/ }), keys: '[MouseLeft]', coords: { clientX: x, clientY: y } });
  await user.click(screen.getByRole('button', { name: 'Cerrar polígono' }));
}
function expectSides(vertices, lengths) {
  edgeLengths(vertices).forEach((side, i) => expect(side).toBeCloseTo(lengths[i], 7));
  expect(validateConvexPolygon(vertices).isValid).toBe(true);
}

test('50/70/65: los tres lados son independientes, los ángulos derivados y el payload canónico', async () => {
  const user = userEvent.setup(); const save = vi.fn();
  render(<CustomPieceEditor onGuardarVertices={save} />);
  await draw(user, 3);
  await user.type(field(1), '50');
  expect(field(2)).toHaveValue(null);
  expect(field(3)).toHaveValue(null);
  await user.type(field(2), '70'); await user.type(field(3), '65');
  expect(field(1)).toHaveValue(50);
  expect(screen.queryByRole('button', { name: /Fijar ángulo/ })).not.toBeInTheDocument();
  expect(screen.getByText(/sin necesidad de fijar ángulos/)).toBeVisible();
  expect(screen.getByRole('img', { name: 'Vista dimensional de la pieza' })).toHaveTextContent('V2 (63°)');
  await user.click(screen.getByRole('button', { name: 'Agregar pieza al pedido' }));
  expect(save).toHaveBeenCalledOnce(); expectSides(save.mock.calls[0][0].vertices, [50, 70, 65]);
});

test('10/10/30: cierre imposible bloquea guardado, explica desigualdad y permite corregir', async () => {
  const user = userEvent.setup(); const save = vi.fn();
  render(<CustomPieceEditor onGuardarVertices={save} />);
  await draw(user, 3); fill([10, 10, 30]);
  expect(screen.getByText(/un lado es demasiado largo/)).toBeVisible();
  expect(screen.getByRole('button', { name: 'Agregar pieza al pedido' })).toBeDisabled();
  expect(screen.queryByRole('region', { name: 'Ángulos interiores' })).not.toBeInTheDocument();
  fill([10, 10, 15]);
  await user.click(screen.getByRole('button', { name: 'Agregar pieza al pedido' }));
  expectSides(save.mock.calls[0][0].vertices, [10, 10, 15]);
});

test('120/73/91/108: cambiar ángulo V2 conserva lados, cambia vértices y persiste la configuración para editar', async () => {
  const user = userEvent.setup(); const changed = vi.fn();
  const { unmount } = render(<CustomPieceEditor onGeometryChange={changed} />);
  await draw(user, 4); fill([120, 73, 91, 108]);
  await user.click(screen.getByRole('button', { name: 'Seleccionar vértice V2' }));
  const angle = screen.getByRole('spinbutton', { name: /Ángulo interior en/ });
  await user.clear(angle); await user.type(angle, '85');
  const first = changed.mock.calls.at(-1)[0];
  await user.clear(angle); await user.type(angle, '110');
  const second = changed.mock.calls.at(-1)[0];
  expectSides(first, [120, 73, 91, 108]); expectSides(second, [120, 73, 91, 108]);
  expect(interiorAngles(second)[1]).toBeCloseTo(110, 7);
  expect(first).not.toEqual(second);
  [120, 73, 91, 108].forEach((value, i) => expect(field(i + 1)).toHaveValue(value));
  await user.clear(angle); await user.type(angle, '1');
  expect(changed.mock.calls.at(-1)[0]).toBeNull();
  expect(screen.getByText(/medidas y ángulos que fijaste chocan/)).toBeVisible();
  await user.clear(angle); await user.type(angle, '110');
  unmount();
});

test('80/115/63/92/71: configura pentágono cíclico explícito y guarda los cinco lados', async () => {
  const user = userEvent.setup(); const save = vi.fn();
  render(<CustomPieceEditor onGuardarVertices={save} />);
  await draw(user, 5); fill([80, 115, 63, 92, 71]);
  expect(screen.getByText(/puedes fijar hasta 2 ángulos/)).toBeVisible();
  expect(screen.getByText('✓ Geometría validada y lista.')).toBeVisible();
  await user.click(screen.getByRole('button', { name: 'Agregar pieza al pedido' }));
  expectSides(save.mock.calls[0][0].vertices, [80, 115, 63, 92, 71]);
  expect(save.mock.calls[0][0].rawState.construction.mode).toBe('cyclic');
});

test('reabrir un cuadrilátero conserva restricción angular y geometría sin inferir otra forma', async () => {
  const user = userEvent.setup(); const save = vi.fn();
  const view = render(<CustomPieceEditor onGuardarVertices={save} />);
  await draw(user, 4); fill([120, 73, 91, 108]);
  await user.click(screen.getByRole('button', { name: 'Seleccionar vértice V2' }));
  fireEvent.change(screen.getByRole('spinbutton', { name: /Ángulo interior en/ }), { target: { value: '110' } });
  await user.click(screen.getByRole('button', { name: 'Agregar pieza al pedido' }));
  const saved = save.mock.calls[0][0]; view.unmount();
  render(<CustomPieceEditor initialState={saved.rawState} onGuardarVertices={save} />);
  expect(screen.getByRole('spinbutton', { name: /Ángulo interior en/ })).toHaveValue(110);
  await user.click(screen.getByRole('button', { name: 'Agregar pieza al pedido' }));
  expect(save.mock.calls[1][0].vertices).toEqual(saved.vertices);
});

test.each([[120,73,91,108], [80,115,63,92,71], [80,115,63,92,71,98]].map(sides => [sides.length, sides]))(
  '%i lados: fijar/liberar por teclado, límite n-3 y longitudes independientes', async (n,sides) => {
    const user=userEvent.setup(); const changed=vi.fn();
    render(<CustomPieceEditor onGeometryChange={changed} />);
    await draw(user,n); fill(sides);
    const base=changed.mock.calls.at(-1)[0];
    for(let vertex=2;vertex<=n-2;vertex++) {
      const select=screen.getByRole('button',{name:`Seleccionar vértice V${vertex}`});
      select.focus(); await user.keyboard('{Enter}');
      const button=screen.getByRole('button',{name:`Fijar ángulo V${vertex}`});
      button.focus(); await user.keyboard('{Enter}');
      expect(Number(screen.getByRole('spinbutton',{name:`Ángulo interior en V${vertex} (grados)`}).value)).toBeGreaterThan(0);
    }
    expect(screen.getByText(`${n-3} / ${n-3} fijados`)).toBeVisible();
    await user.click(screen.getByRole('button',{name:'Seleccionar vértice V1'}));
    expect(screen.getByRole('button',{name:'Fijar ángulo V1'})).toBeDisabled();
    const angle=screen.getByRole('spinbutton',{name:/Ángulo interior en V2/});
    fireEvent.change(angle,{target:{value:String(Number(angle.value)-5)}});
    const next=changed.mock.calls.at(-1)[0];
    expectSides(next,sides); expect(next).not.toEqual(base);
    expect(interiorAngles(next).reduce((a,b)=>a+b)).toBeCloseTo((n-2)*180,5);
    sides.forEach((side,i)=>expect(field(i+1)).toHaveValue(side));
    await user.click(screen.getByRole('button',{name:'Liberar ángulo V2'}));
    await user.click(screen.getByRole('button',{name:'Seleccionar vértice V1'}));
    await user.click(screen.getByRole('button',{name:'Fijar ángulo V1'}));
    expect(screen.getByRole('spinbutton',{name:/Ángulo interior en V1/})).toBeVisible();
    expect(screen.queryByRole('spinbutton',{name:/Ángulo interior en V2/})).not.toBeInTheDocument();
    expect(screen.getByRole('img',{name:'Vista dimensional de la pieza'})).toHaveTextContent('°');
  });

test('restricción inválida retira payload y preview, conserva inputs y se puede liberar', async () => {
  const user=userEvent.setup(); const changed=vi.fn();
  render(<CustomPieceEditor onGeometryChange={changed} />);
  await draw(user,5); fill([80,115,63,92,71]);
  await user.click(screen.getByRole('button',{name:'Seleccionar vértice V2'}));
  await user.click(screen.getByRole('button',{name:'Fijar ángulo V2'}));
  const input=screen.getByRole('spinbutton',{name:/Ángulo interior en/});
  for(const value of ['0','-1','180','']) {
    fireEvent.change(input,{target:{value}});
    expect(input).toHaveAttribute('aria-invalid','true');
    expect(changed.mock.calls.at(-1)[0]).toBeNull();
    expect(screen.getByRole('img',{name:'Vista dimensional de la pieza'}).querySelector('polygon')).toHaveAttribute('data-provisional','true');
    [80,115,63,92,71].forEach((side,i)=>expect(field(i+1)).toHaveValue(side));
  }
  await user.click(screen.getByRole('button',{name:'Liberar ángulo V2'}));
  expectSides(changed.mock.calls.at(-1)[0],[80,115,63,92,71]);
});
