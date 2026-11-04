import { useId } from 'react';
import { SHAPE_NAMES, describeOriginalMeasures, formatMm } from './originalMeasures';
import './OriginalMeasuresTable.css';

// TA-046 T02: medidas que ingresó el usuario, visibles junto al resultado (SPEC-TA-046 RN-07 y RN-09).
export function OriginalMeasuresTable({ pieces }) {
  const noteId = useId();
  if (!pieces?.length) return null;
  return (
    <section className="original-measures" aria-describedby={noteId}>
      <p id={noteId} className="original-measures__note">
        Medidas ingresadas en el pedido, en mm. En el resultado las piezas pueden aparecer giradas.
      </p>
      <div className="original-measures__scroll" role="region" aria-label="Medidas originales con desplazamiento horizontal" tabIndex={0}>
        <table className="original-measures__table">
          <caption>Medidas originales del pedido</caption>
          <thead>
            <tr><th scope="col">Pedido</th><th scope="col">Pieza</th><th scope="col">Forma</th><th scope="col">Cantidad</th><th scope="col">Vidrio</th><th scope="col">Medidas</th></tr>
          </thead>
          <tbody>
            {pieces.map(piece => (
              <tr key={piece.id_pieza}>
                <td>#{piece.id_pedido}</td>
                <th scope="row">#{piece.id_pieza}</th>
                <td>{SHAPE_NAMES[piece.tipo_forma] ?? piece.tipo_forma}</td>
                <td>{piece.cantidad}</td>
                <td>{piece.material_nombre ?? `Vidrio #${piece.id_tipo_vidrio}`} · {formatMm(piece.espesor_mm)} mm</td>
                <td>{describeOriginalMeasures(piece)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}