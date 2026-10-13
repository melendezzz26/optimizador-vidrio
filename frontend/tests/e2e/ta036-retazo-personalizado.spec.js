import { test, expect } from '@playwright/test';
import { edgeLengths, interiorAngles } from '../../src/features/orders/polygonMeasurements.js';

test('retazo personalizado: editor compartido, POST real sin Decimal no serializable y lectura numérica', async ({page,baseURL},testInfo) => {
  const api='http://127.0.0.1:8017';
  await page.route('**/*',route => [baseURL,api].includes(new URL(route.request().url()).origin) ? route.continue() : route.abort());
  await page.goto('/');
  await page.getByLabel('Usuario',{exact:true}).fill('A70000002');
  await page.getByLabel('Contraseña',{exact:true}).fill('Inventory-test-2026!');
  await page.getByRole('button',{name:'Ingresar',exact:true}).click();
  await page.getByRole('complementary',{name:'Módulos de NewGlass'}).getByRole('button',{name:'Gestión de inventario'}).click();
  await page.getByRole('tab',{name:'Retazos',exact:true}).click();
  await page.getByRole('button',{name:'Registrar retazo',exact:true}).click();
  const code=`ANG-${testInfo.project.name}`;
  await page.getByLabel(/Código/).fill(code);
  await page.getByLabel(/Tipo de vidrio/).selectOption('7');
  await page.getByLabel(/Espesor/).selectOption('6');
  await page.getByLabel(/Tipo de forma/).selectOption('POLIGONO_CONVEXO');
  const canvas=page.getByRole('img',{name:/Lienzo del dibujo original/});
  await canvas.scrollIntoViewIfNeeded();
  for(const point of [[100,100],[500,100],[500,400],[100,400]]) {
    const p=await canvas.evaluate((svg,[x,y])=>{const p=new DOMPoint(x,y).matrixTransform(svg.getScreenCTM());return {x:p.x,y:p.y};},point);
    await page.mouse.click(p.x,p.y);
  }
  await page.getByRole('button',{name:'Cerrar polígono'}).click();
  const sides=[120,73,91,108];
  for(const [i,value] of sides.entries()) await page.getByLabel(`Longitud del segmento S${i+1} en milímetros`).fill(String(value));
  await page.getByRole('button',{name:'Fijar ángulo V2',exact:true}).click();
  await page.getByRole('spinbutton',{name:/Ángulo interior fijado en V2/}).fill('100');
  const saved=page.waitForResponse(r=>r.url()===`${api}/api/inventory/retazos` && r.request().method()==='POST');
  await page.getByRole('button',{name:'Registrar retazo',exact:true}).last().click();
  const response=await saved; expect(response.status()).toBe(201);
  await expect(page.getByRole('row',{name:new RegExp(code)})).toBeVisible();
  const read=await page.request.get(`${api}/api/inventory/retazos`,{headers:{Authorization:response.request().headers().authorization}});
  expect(read.status()).toBe(200);
  const row=(await read.json()).find(row=>row.codigo===code);
  expect(row).toBeTruthy();
  expect(row.geometria.vertices_mm.flat().every(value=>typeof value==='number')).toBe(true);
  edgeLengths(row.geometria.vertices_mm).forEach((side,i)=>expect(side).toBeCloseTo(sides[i],5));
  expect(interiorAngles(row.geometria.vertices_mm)[1]).toBeCloseTo(100,5);
});
