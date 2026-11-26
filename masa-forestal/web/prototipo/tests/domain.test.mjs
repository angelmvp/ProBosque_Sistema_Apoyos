import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { normalize, parsePeriod, periodLabel, previousPeriod, availablePeriods, validateFilters, delta, buildHistory, demoRecord, isOpen, restrictReferences } from '../dist/domain.js';
const snapshot=JSON.parse(readFileSync(new URL('../dist/data/piloto.json',import.meta.url)));
const geo=JSON.parse(readFileSync(new URL('../dist/data/municipios.json',import.meta.url)));
const municipalities=geo.features.map(f=>f.properties);
const params=(from='2021',to='2025',frequency='anual',municipality='15110')=>({from,to,frequency,municipality});
test('catálogo completo, claves únicas, áreas positivas y geometrías solo visuales',()=>{
  assert.equal(municipalities.length,125);assert.equal(new Set(municipalities.map(m=>m.id)).size,125);assert.equal(geo.displayOnly,true);
  for(const m of municipalities){assert.match(m.id,/^15\d{3}$/);assert.ok(m.areaHa>0);assert.ok(m.name);}
});
test('calendario anual inclusivo, sin duplicar periodos',()=>assert.deepEqual(validateFilters(params('2023','2025'),municipalities,snapshot.cutoff),['2023','2024','2025']));
test('calendario bimestral cruza el año usando bimestres naturales',()=>{
  assert.deepEqual(validateFilters(params('2024-B6','2025-B2','bimestral'),municipalities,snapshot.cutoff),['2024-B6','2025-B1','2025-B2']);
  assert.equal(previousPeriod('2025-B1'),'2024-B6');assert.equal(periodLabel('2025-B2'),'Mar–Abr 2025');
});
test('no permite municipio desconocido, frecuencia inválida, rango invertido ni futuro',()=>{
  for(const p of [params('2025','2024'),params('2027','2027'),params('2025','2025','mensual'),params('2025','2025','anual','99999'),params('2016','2020'),params('2025-B7','2025-B7','bimestral')])assert.throws(()=>validateFilters(p,municipalities,snapshot.cutoff));
});
test('bimestre futuro no aparece; el abierto sí',()=>{
  assert.equal(availablePeriods('bimestral','2026-09-15').at(-1),'2026-B5');
  assert.equal(isOpen('2026-B5','2026-09-15'),true);assert.equal(isOpen('2026-B4','2026-09-15'),false);
  assert.throws(()=>parsePeriod('2025-B7'));
});
test('cambio absoluto y porcentual distingue ausencia, cero, ganancia y pérdida',()=>{
  assert.deepEqual(delta(110,100),{ha:10,pct:10});assert.deepEqual(delta(90,100),{ha:-10,pct:-10});
  assert.deepEqual(delta(100,100),{ha:0,pct:0});assert.deepEqual(delta(0,100),{ha:-100,pct:-100});
  assert.deepEqual(delta(10,0),{ha:10,pct:null});assert.deepEqual(delta(0,0),{ha:0,pct:null});
  assert.deepEqual(delta(null,100),{ha:null,pct:null});assert.deepEqual(delta(100,null),{ha:null,pct:null});
  assert.deepEqual(delta(110,100,false),{ha:null,pct:null});
});
test('el hueco de 2023 no se interpola ni se salta como referencia para 2024',()=>{
  const rows=buildHistory('demo',params(),municipalities,snapshot);
  assert.equal(rows[2].period,'2023');assert.equal(rows[2].forestHa,null);assert.equal(rows[3].reference,'2023');assert.equal(rows[3].change.ha,null);
  assert.ok(rows[4].change.ha<0);
});
test('la primera fila obtiene la referencia fuera del rango y admite un único periodo',()=>{
  const rows=buildHistory('demo',params('2025','2025'),municipalities,snapshot);
  assert.equal(rows.length,1);assert.equal(rows[0].reference,'2024');assert.ok(rows[0].referenceHa>0);assert.ok(rows[0].change.ha<0);
});
test('el primer año seleccionable no falla al buscar la referencia de 2016',()=>{
  assert.equal(buildHistory('real',params('2017','2017'),municipalities,snapshot)[0].reference,'2016');
  assert.ok(buildHistory('demo',params('2017','2017'),municipalities,snapshot)[0].forestHa>0);
});
test('un periodo abierto se identifica como provisional y no tiene cambios',()=>{
  for(const [period,freq] of [['2026','anual'],['2026-B6','bimestral']]){
    const row=buildHistory('demo',params(period,period,freq),municipalities,snapshot)[0];
    assert.equal(row.status,'en_curso');assert.deepEqual(row.change,{ha:null,pct:null});
  }
});
test('piloto real no convierte calidad SCL en hectáreas ni cobertura por área',()=>{
  const rows=buildHistory('real',params('2025-B1','2025-B2','bimestral'),municipalities,snapshot);
  for(const row of rows){assert.equal(row.forestHa,null);assert.equal(row.coveragePct,null);assert.equal(row.change.ha,null);assert.equal(row.status,'pendiente_validacion');assert.ok(row.observationPct>0);}
  assert.equal(rows[0].observationPct,92.78129649816593);
});
test('cartografía real usa fuente propia, clases forestales y referencia inmediata',()=>{
  const rows=buildHistory('real',params('2024','2025'),municipalities,snapshot);
  assert.ok(Math.abs(rows[1].forestHa-32280.54728552795)<1e-8);
  assert.ok(Math.abs(rows[1].change.ha-347.6207806382777)<1e-8);
  assert.ok(Math.abs(rows[0].referenceHa-31872.550151087235)<1e-8);
  assert.equal(rows[1].status,'cartografia_publica');assert.equal(rows[1].forestValidated,false);
  assert.match(rows[1].geometryVersion,/MapBiomas/);assert.equal(rows[1].temporalGapfill,true);
  assert.ok(rows[1].referenceAreaHa!==municipalities.find(m=>m.id==='15110').areaHa);
});
test('no se mezclan fuentes o versiones ni se salta un año en la cartografía',()=>{
  for(const mutate of [r=>r.source='cdse',r=>r.sourceFingerprint='otro',r=>r.geometryVersion='INEGI',r=>r.period='2015']){
    const copy=structuredClone(snapshot); mutate(copy.records.find(r=>r.period==='2024'));
    assert.deepEqual(buildHistory('real',params('2025','2025'),municipalities,copy)[0].change,{ha:null,pct:null});
  }
});
test('los 125 municipios tienen series anuales propias y referencia de 2016',()=>{
  assert.equal(Object.keys(snapshot.municipalRecords).length,125);
  for(const m of municipalities){
    const rows=buildHistory('real',params('2017','2025','anual',m.id),municipalities,snapshot);
    assert.equal(rows.length,9);assert.equal(rows[0].reference,'2016');
    for(const r of rows){assert.equal(r.municipality,m.id);assert.equal(r.status,'cartografia_publica');assert.ok(r.forestHa>=0);assert.ok(r.change.ha!==null);assert.equal(r.forestValidated,false);}
  }
  assert.ok(Math.abs(buildHistory('real',params('2025','2025','anual','15106'),municipalities,snapshot)[0].forestHa-9428.05491685701)<1e-8);
});
test('la superficie cero se muestra y conserva un cambio absoluto cero',()=>{
  const r=buildHistory('real',params('2025','2025','anual','15030'),municipalities,snapshot)[0];
  assert.equal(r.forestHa,0);assert.deepEqual(r.change,{ha:0,pct:null});assert.equal(r.status,'cartografia_publica');
});
test('los bimestres municipales no reutilizan las superficies anuales',()=>{
  for(const m of municipalities) for(const row of buildHistory('real',params('2025-B1','2025-B6','bimestral',m.id),municipalities,snapshot)){
    assert.equal(row.forestHa,null);assert.equal(row.change.ha,null);
  }
});
test('una fila de otro municipio no aparece en el historial seleccionado',()=>{
  const copy=structuredClone(snapshot);copy.municipalRecords['15106']=copy.records;
  assert.equal(buildHistory('real',params('2025','2025','anual','15106'),municipalities,copy)[0].forestHa,null);
});
test('un fallo de integridad del servidor elimina también los colores estáticos',()=>{
  const filtered=restrictReferences(snapshot,{cutoff:snapshot.cutoff,referenceMunicipalities:['15106']});
  assert.equal(buildHistory('real',params('2025','2025'),municipalities,filtered)[0].forestHa,null);
  assert.ok(buildHistory('real',params('2025','2025','anual','15106'),municipalities,filtered)[0].forestHa>0);
  const failed=restrictReferences(snapshot,{cutoff:snapshot.cutoff,referenceError:true,referenceMunicipalities:['15110']});
  assert.deepEqual(failed.municipalRecords,{});
  assert.equal(buildHistory('real',params('2025','2025'),municipalities,failed)[0].forestHa,null);
});
test('demostración siempre rotulada, reproducible y acotada por el área municipal',()=>{
  for(const m of municipalities){const a=demoRecord(m,'2025',snapshot.cutoff);assert.equal(a.simulated,true);assert.ok(a.forestHa>=0&&a.forestHa<=m.areaHa);assert.deepEqual(a,demoRecord(m,'2025',snapshot.cutoff));}
});
test('la búsqueda no depende de acentos o mayúsculas',()=>assert.equal(normalize('  MÉXICO  '),'mexico'));
