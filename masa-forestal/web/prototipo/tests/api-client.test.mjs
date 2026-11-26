import test from 'node:test';
import assert from 'node:assert/strict';
import { createApiClient, ServiceError, delay } from '../dist/api-client.js';
const params={municipality:'15110',frequency:'bimestral',from:'2025-B1',to:'2025-B1'};
const id='a'.repeat(32);
const history={municipality:'15110',rows:[{period:'2025-B1',forestHa:null}]};
const reply=(data,ok=true)=>({ok,json:async()=>data});
test('trabajo en segundo plano termina leyendo el historial del servidor',async()=>{
  const calls=[],statuses=[],responses=[{id,status:'pendiente'},{id,status:'procesando'},{id,status:'completado'},history];
  const api=createApiClient({fetcher:async(url,options)=>{calls.push({url,options});return reply(responses.shift());},wait:async()=>{}});
  assert.deepEqual(await api.update(params,{onProgress:job=>statuses.push(job.status)}),history);
  assert.deepEqual(statuses,['pendiente','procesando','completado']);
  assert.equal(calls[0].options.headers['X-MAF-Request'],'1');assert.deepEqual(JSON.parse(calls[0].options.body),params);
  assert.match(calls.at(-1).url,/^\/api\/historial\?/);
});
test('fallo CDSE conserva su mensaje y no inventa un historial vacío',async()=>{
  const api=createApiClient({fetcher:async()=>reply({id,status:'fallido',message:'CDSE rechazó las credenciales.',error_code:'cdse_http_401'})});
  await assert.rejects(api.update(params),error=>error instanceof ServiceError&&error.code==='cdse_http_401');
});
test('cancelar seguimiento impide que una respuesta tardía complete la consulta',async()=>{
  const controller=new AbortController();let calls=0;
  const api=createApiClient({fetcher:async()=>{calls++;return reply({id,status:'procesando'});},wait:async()=>controller.abort()});
  await assert.rejects(api.update(params,{signal:controller.signal}),{name:'AbortError'});assert.equal(calls,1);
});
test('errores de red y respuesta malformada se muestran como fallos recuperables',async()=>{
  const offline=createApiClient({fetcher:async()=>{throw new Error('private internals');}});
  await assert.rejects(offline.history(params),e=>e instanceof ServiceError&&!e.message.includes('private'));
  const malformed=createApiClient({fetcher:async()=>reply({municipality:'15106',rows:[]})});
  await assert.rejects(malformed.history(params),{code:'respuesta_invalida'});
});
test('un error de validación HTTP no inicia el sondeo',async()=>{
  let calls=0;const api=createApiClient({fetcher:async()=>{calls++;return reply({error:{code:'fuera_del_piloto',message:'Fuera del piloto.'}},false);}});
  await assert.rejects(api.update(params),{code:'fuera_del_piloto'});assert.equal(calls,1);
});
test('el intervalo de sondeo puede abortarse inmediatamente',async()=>{
  const controller=new AbortController();const pending=delay(10000,controller.signal);controller.abort();await assert.rejects(pending,{name:'AbortError'});
});
