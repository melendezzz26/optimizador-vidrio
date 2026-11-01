import { test, expect } from '@playwright/test';
import { api, setup, login, open, stock, capture, save } from './optimizationRealSupport.js';

function contour(geometry) {
  if (geometry.type === 'RECTANGULO') return [[0,0],[geometry.width_mm,0],[geometry.width_mm,geometry.height_mm],[0,geometry.height_mm]].map(p=>p.map(Number));
  if (geometry.type === 'CIRCUNFERENCIA') return Array.from({length:96},(_,i)=>[
    Number(geometry.radius_mm)*(1+Math.cos(i*Math.PI/48)),Number(geometry.radius_mm)*(1+Math.sin(i*Math.PI/48))]);
  const xs=geometry.vertices_mm.map(p=>Number(p[0])),ys=geometry.vertices_mm.map(p=>Number(p[1]));
  return geometry.vertices_mm.map(([x,y])=>[Number(x)-Math.min(...xs),Number(y)-Math.min(...ys)]);
}

for (const scenario of ['differential','mixed']) test(`políticas reales ${scenario}: fuentes y contornos 2D/3D corresponden al backend`, async ({page},info)=>{
  const data=await setup(page,'combined',{createOrders:false});
  const dimensions=scenario==='differential'?[[1000,700],[700,500]]:[[75,60],[60,50]];
  const sources=[];
  // B is created first so A is newer: the real adapter must offer A before B.
  for(const index of [1,0]) {
    const [width_mm,height_mm]=dimensions[index];
    const response=await page.request.post(`${api}/api/inventory/retazos`,{headers:data.headers,data:{...data.materials[0],
      codigo:`POL-${scenario}-${info.project.name}-${index}`,geometria:{type:'RECTANGULO',width_mm,height_mm}}});
    expect(response.status()).toBe(201);
    sources[index]=(await response.json()).id_retazo;
    data.remnants.push(sources[index]);
  }
  const piezas=scenario==='differential'?[{...data.materials[0],tipo_forma:'RECTANGULO',cantidad:1,width_mm:600,height_mm:400}]:[
    {...data.materials[0],tipo_forma:'RECTANGULO',cantidad:2,width_mm:30,height_mm:20},
    {...data.materials[1],tipo_forma:'CIRCUNFERENCIA',cantidad:1,radius_mm:8},
    {...data.materials[0],tipo_forma:'POLIGONO_CONVEXO',cantidad:2,vertices_mm:[[0,0],[24,0],[3,17]]}];
  const created=await page.request.post(`${api}/api/orders`,{headers:data.headers,data:{id_cliente:41,piezas}});
  expect(created.status()).toBe(201);data.orders.push((await created.json()).id_pedido);
  const before=await stock(page,data);
  await login(page,data.actors.all,{comparative:true});await open(page);
  await page.getByRole('checkbox',{name:new RegExp(`Pedido #${data.orders[0]}\\b`)}).check();
  const accepted=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/optimization/comparisons'&&r.request().method()==='POST');
  await page.getByRole('button',{name:'Comparar con los tres motores',exact:true}).click();
  const response=await accepted;expect(response.status()).toBe(201);
  const current=await response.json(),results={};
  await expect(page.getByText('Comparación finalizada',{exact:true})).toBeVisible();
  for(const execution of current.executions) {
    const method=execution.method,name={FF:'First Fit',BF:'Best Fit',WF:'Worst Fit'}[method];
    const canonical=await page.request.get(`${api}/api/optimization/comparisons/${current.comparison_id}/executions/${execution.execution_id}`,{headers:data.headers});
    expect(canonical.status()).toBe(200);
    const dto=(await canonical.json()).result;results[method]=dto;
    expect(dto.metodo).toBe(method);
    await page.getByRole('tab',{name:new RegExp(name)}).click();
    const panel=page.getByRole('tabpanel',{name:new RegExp(name)});
    await panel.getByRole('button',{name:/Resultado/}).click();
    await expect(panel.getByRole('heading',{name:`Resultado de ${name}`,exact:true})).toBeVisible();
    const canvas=panel.getByRole('region',{name:'Distribución de piezas',exact:true});
    for(const material of dto.materials_used) {
      const own=dto.placements.filter(p=>p.material_source===material.material_source&&p.material_id===material.material_id&&p.stock_unit_index===material.stock_unit_index);
      const key=`${material.material_source}:${material.material_id}:${material.stock_unit_index}`;
      await canvas.getByLabel('Vidrio del resultado').selectOption(`${material.id_tipo_vidrio}:${Number(material.espesor_mm)}`);
      await canvas.getByLabel('Plancha o retazo',{exact:true}).selectOption(key);
      await canvas.getByRole('button',{name:'Ver en 2D',exact:true}).click();
      const boundary=contour(material.geometria),width=Math.max(...boundary.map(p=>p[0])),height=Math.max(...boundary.map(p=>p[1]));
      await expect(canvas.locator('svg.first-fit-sheet')).toHaveAttribute('viewBox',`0 0 ${width} ${height}`);
      await expect(canvas.locator('[data-placement]')).toHaveCount(own.length);
      for(const p of own) {
        const piece=canvas.locator(`[data-placement="${p.id_pedido}:${p.id_pieza}:${p.unit_index}"]`);
        const translation=(await piece.getAttribute('transform')).match(/[-\d.]+/g).map(Number);
        expect(translation).toEqual([Number(p.x_mm),Number(p.y_mm)]);
        if(p.geometria.type==='RECTANGULO') {
          await expect(piece.locator('g > rect')).toHaveAttribute('width',String(p.geometria.width_mm));
          await expect(piece.locator('g > rect')).toHaveAttribute('height',String(p.geometria.height_mm));
        } else if(p.geometria.type==='CIRCUNFERENCIA') await expect(piece.locator('g > circle')).toHaveAttribute('r',String(p.geometria.radius_mm));
        else await expect(piece.locator('g > polygon')).toHaveAttribute('points',p.geometria.vertices_mm.map(v=>v.join(',')).join(' '));
      }
      await canvas.getByRole('button',{name:'Ver en 3D',exact:true}).click();
      await canvas.getByRole('button',{name:'Vista superior',exact:true}).click();
      await expect(canvas.locator('[data-piece-3d]')).toHaveCount(own.length);
      for(const p of own) {
        const piece=canvas.locator(`[data-piece-3d="${p.id_pedido}:${p.id_pieza}:${p.unit_index}"]`);
        // Independent top-camera projection: yaw=0, pitch=90°, depth=25.
        const factor=1000/Math.max(width,height)*2400/(2400-25);
        const expected=contour(p.geometria).flatMap(([x,y])=>[
          (Number(p.x_mm)+x-width/2)*factor,(Number(p.y_mm)+y-height/2)*factor]);
        const projected=(await piece.locator(':scope > path').last().getAttribute('d')).match(/-?\d+(?:\.\d+)?/g).map(Number);
        expect(projected.length).toBe(expected.length);
        projected.forEach((value,i)=>expect(Math.abs(value-expected[i])).toBeLessThan(.001));
      }
    }
    await capture(page,info,`${scenario}-${method}-backend-3d`,panel);
  }
  if(scenario==='differential') {
    expect(results.FF.placements[0].material_id).toBe(sources[0]);
    expect(results.BF.placements[0].material_id).toBe(sources[1]);
    expect(results.WF.placements[0].material_id).toBe(sources[0]);
  }
  expect(await stock(page,data)).toEqual(before);
  save(info,`${scenario}-backend-results.json`,results);
});
