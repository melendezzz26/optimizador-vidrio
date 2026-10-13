import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, test, vi } from 'vitest'
import RegistrarRetazoForm from '../RegistrarRetazoForm'

const catalogo = [{ id_tipo_vidrio: 1, nombre: 'Incoloro', estado: true, espesores_mm: [6] }]
const canvas = () => screen.getByRole('img', { name: /Lienzo del dibujo original/ })

async function setup() {
  const onSubmit = vi.fn()
  const user = userEvent.setup()
  render(<RegistrarRetazoForm catalogo={catalogo} onSubmit={onSubmit} />)
  await user.type(screen.getByLabelText(/Código/), 'R-POL')
  await user.selectOptions(screen.getByLabelText(/Tipo de vidrio/), '1')
  await user.selectOptions(screen.getByLabelText(/Espesor/), '6')
  await user.selectOptions(screen.getByLabelText(/Tipo de forma/), 'POLIGONO_CONVEXO')
  return { user, onSubmit }
}

async function draw(user) {
  for (const [x,y] of [[100,100],[400,100],[500,300],[200,300]]) {
    await user.pointer({ target: canvas(), keys: '[MouseLeft]', coords: { clientX:x, clientY:y } })
  }
  await user.click(screen.getByRole('button',{name:'Cerrar polígono'}))
  fireEvent.change(screen.getByLabelText('Longitud del segmento S1 en milímetros'), { target:{value:'600'} })
}

describe('TA-036: retazo con editor compartido', () => {
  test('reutiliza dibujo, escala y ángulos; envía vertices_mm sin otro editor de coordenadas',async()=>{
    const {user,onSubmit}=await setup()
    expect(screen.getByRole('region',{name:'Geometría del retazo'})).toBeVisible()
    expect(screen.queryByLabelText(/coordenada X/)).not.toBeInTheDocument()
    await draw(user)
    expect(screen.getByRole('region',{name:'Ángulos interiores'})).toBeVisible()
    expect(screen.queryByRole('button',{name:'Agregar pieza al pedido'})).not.toBeInTheDocument()
    await user.click(screen.getByRole('button',{name:'Registrar retazo',exact:true}))
    await waitFor(()=>expect(onSubmit).toHaveBeenCalledOnce())
    expect(onSubmit).toHaveBeenCalledWith({codigo:'R-POL',id_tipo_vidrio:1,espesor_mm:6,
      geometria:{type:'POLIGONO_CONVEXO',vertices_mm:[[0,0],[600,0],[800,400],[200,400]]}})
  })

  test('reiniciar después de una figura válida invalida el payload anterior',async()=>{
    const {user,onSubmit}=await setup()
    await draw(user)
    await user.click(screen.getByRole('button',{name:'Reiniciar dibujo'}))
    await user.click(screen.getByRole('button',{name:'Registrar retazo',exact:true}))
    expect(onSubmit).not.toHaveBeenCalled()
    expect(screen.getByText('Cierra y dimensiona un polígono convexo válido en el editor.')).toBeVisible()
  })

  test('edición carga y guarda la forma existente usando el editor compartido',async()=>{
    const onSubmit=vi.fn(); const user=userEvent.setup()
    render(<RegistrarRetazoForm catalogo={catalogo} mode="edit" onSubmit={onSubmit}
      initialValues={{codigo:'R-OLD',id_tipo_vidrio:1,espesor_mm:6,
        geometria:{type:'POLIGONO_CONVEXO',vertices_mm:[[0,0],[600,0],[800,400],[200,400]]}}} />)
    expect(screen.getByText('Polígono cerrado')).toBeVisible()
    await user.click(screen.getByRole('button',{name:'Guardar cambios'}))
    await waitFor(()=>expect(onSubmit).toHaveBeenCalledOnce())
    const points=onSubmit.mock.calls[0][0].geometria.vertices_mm
    points.forEach((point,i)=>point.forEach((value,axis)=>expect(value).toBeCloseTo([[0,0],[600,0],[800,400],[200,400]][i][axis],8)))
  })
})
