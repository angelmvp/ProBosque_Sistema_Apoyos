import { normalize, periodLabel, parsePeriod, availablePeriods, validateFilters, buildHistory, getRecord, isReference, restrictReferences } from './domain.js';
import { createApiClient, ServiceError } from './api-client.js';

const local = window.MAF_RUNTIME?.mode === 'local';
const api = createApiClient();

const $ = id => document.getElementById(id);
const state = { municipality: '15110', municipalities: [], features: [], snapshot: null, rows: [], selected: null, request: 0, controller: null, paths: new Map(), bounds: new Map(), view: [0, 0, 760, 660] };
const number = new Intl.NumberFormat('es-MX', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const fmt = value => value == null ? '—' : number.format(value);
const signed = value => value == null ? '—' : `${value > 0 ? '+' : ''}${fmt(value)}`;
const element = (tag, className, text) => { const node = document.createElement(tag); if (className) node.className = className; if (text != null) node.textContent = text; return node; };
const svgNode = (tag, attrs) => { const node = document.createElementNS('http://www.w3.org/2000/svg', tag); for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value); return node; };
const municipality = () => state.municipalities.find(m => m.id === state.municipality);
const filters = () => ({ municipality: state.municipality, frequency: 'anual', from: $('from-period').value, to: $('to-period').value });
const dateText = value => value ? new Date(value).toLocaleString('es-MX', { timeZone: 'America/Mexico_City', dateStyle: 'medium', timeStyle: 'short' }).replace(/\.$/, '') : 'Sin actualización';
function localControls(busy = false) {
  $('local-controls').hidden = !local;
  if (!local || !state.backend) return;
  let supported = false;
  try { supported = state.backend.processingMunicipalities?.includes(state.municipality) && validateFilters(filters(), state.municipalities, state.snapshot.cutoff).every(p => state.backend.supportedPeriods.includes(p)); } catch {}
  $('refresh-cdse').disabled = busy || !supported || !state.backend.credentialsConfigured;
  $('processing-scope').textContent = !state.backend.credentialsConfigured ? 'El historial anual público se puede consultar. Faltan las credenciales para actualizar CDSE.' : supported ? 'Revisa imágenes y calidad Sentinel de este municipio. Reutiliza diagnósticos recientes y reanuda trabajos interrumpidos. Las hectáreas anuales proceden de MapBiomas.' : 'CDSE permite revisar años completos desde 2017. El año en curso todavía no se procesa como resultado anual.';
}
function message(text, kind = '') { $('query-message').hidden = !text; $('query-message').className = `message ${kind}`; $('query-message').textContent = text; }
function loading(value) { $('query-button').disabled = value || !state.snapshot; $('query-button').querySelector('span').textContent = value ? 'Consultando historial…' : 'Consultar historial'; $('history-table').setAttribute('aria-busy', String(value)); localControls(value); }
function badge(record) {
  const variants = { cartografia_publica: ['data', 'Cartografía'], cartografia_parcial: ['pending', 'Parcial'], pendiente_validacion: ['pending', 'Por validar'], con_datos: ['data', 'Con datos'], sin_registros: ['', 'Sin datos'], en_curso: ['open', 'En curso'], no_habilitado: ['', 'No habilitado'], sin_procesar: ['pending', 'Sin procesar'] };
  const [kind, label] = variants[record.status] || ['', 'No disponible'];
  return element('span', `badge ${kind}`, label);
}
function clearResults(text = 'Filtros actualizados. Pulsa Consultar historial para ver los resultados.') {
  state.controller?.abort(); state.request++; state.rows = []; state.selected = null;
  $('history-body').replaceChildren(); $('timeline').replaceChildren(element('p', 'secondary', 'Consulta el historial para seleccionar un periodo.'));
  $('result-count').textContent = '—'; $('result-context').textContent = 'Consulta pendiente';
  $('detail-title').textContent = 'Detalle de la consulta'; $('detail-status').replaceChildren();
  $('detail-content').replaceChildren(element('p', 'secondary', 'Selecciona los filtros y consulta el historial.'));
  $('form-error').hidden = true; $('municipality-input').removeAttribute('aria-invalid'); $('announcement').textContent = '';
  message(text); loading(false); updateMap();
}
function populatePeriods() {
  if (!state.snapshot) return;
  const periods = availablePeriods('anual', state.snapshot.cutoff);
  for (const id of ['from-period', 'to-period']) $(''+id).replaceChildren(...periods.map(p => new Option(periodLabel(p), p)));
  $('from-period').value = '2024';
  $('to-period').value = '2025';
}
async function query({ update = false } = {}) {
  if (!state.snapshot) return;
  const params = filters();
  try { validateFilters(params, state.municipalities, state.snapshot.cutoff); }
  catch (error) { $('form-error').textContent = error.message; $('form-error').hidden = false; if (!params.municipality) $('municipality-input').setAttribute('aria-invalid', 'true'); return; }
  clearResults('');
  const request = ++state.request;
  state.controller = new AbortController();
  loading(true); message('Consultando historial…', 'loading');
  try {
    if (local) {
      const signal = state.controller.signal;
      const result = update ? await api.update(params, { signal, onProgress: job => {
        if (request === state.request) message(`${job.message} Periodos: ${job.completed} de ${job.total}.`, 'loading');
      } }) : await api.history(params, signal);
      if (request !== state.request) return;
      state.rows = result.rows;
      state.snapshot = { ...state.snapshot, cutoff: result.cutoff, municipality: params.municipality, records: result.rows };
    } else {
      const response = await fetch('./data/piloto.json', { cache: 'no-store', signal: state.controller.signal });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      let snapshot = await response.json();
      if (request !== state.request) return;
      if (!Array.isArray(snapshot.records) || !/^\d{4}-\d{2}-\d{2}$/.test(snapshot.cutoff)) throw new Error('Respuesta incompleta');
      if (local) snapshot = restrictReferences(snapshot, state.backend);
      state.snapshot = snapshot;
      state.rows = buildHistory('real', params, state.municipalities, snapshot);
    }
    state.selected = state.rows.at(-1).period;
    $('result-context').textContent = `${municipality().name} · Anual`;
    $('result-count').textContent = `${state.rows.length} periodo${state.rows.length === 1 ? '' : 's'}`;
    const pending = state.rows.some(r => r.status === 'pendiente_validacion');
    const numeric = state.rows.some(r => r.forestHa != null);
    if (local && state.backend.referenceError) message('La cartografía guardada no pasó las comprobaciones de integridad. No se muestran sus superficies. Revisa los archivos de referencia.', 'error');
    else if (pending) message('Hay observaciones CDSE. La estimación de bosque de estos periodos requiere referencias revisadas y evaluación del clasificador; aún no se publican hectáreas.', 'warning');
    else if (state.rows.some(r => r.status === 'referencia_invalida')) message('La referencia de este municipio no pasó las comprobaciones de integridad. No se muestran sus superficies.', 'error');
    else if (state.rows.some(r => r.status === 'no_habilitado')) message('No hay superficies disponibles para estos años. La cartografía pública disponible comprende 2017–2025.', 'warning');
    else if (state.rows.some(r => r.status === 'sin_procesar')) message('Hay periodos sin procesar. Actualiza CDSE para revisar su disponibilidad.', 'warning');
    else if (!numeric) message('No hay registros históricos disponibles para este municipio y los periodos seleccionados.', 'warning');
    else if (state.rows.some(isReference)) message('Superficie anual de la cartografía pública MapBiomas. Exactitud local sin evaluar; los cambios son diferencias entre mapas.', '');
    else message('');
    renderHistory(); selectPeriod(state.selected);
    $('announcement').textContent = `Consulta completada: ${state.rows.length} periodos para ${municipality().name}.`;
  } catch (error) {
    if (error.name === 'AbortError' || request !== state.request) return;
    message(error instanceof ServiceError ? `${error.message} Tus filtros se conservan. ${update ? 'Puedes reintentar con Actualizar CDSE o consultar el historial guardado.' : 'Pulsa Consultar historial para reintentar.'}` : 'No fue posible consultar el historial. Conservamos tus filtros; pulsa Consultar historial para reintentar.', 'error');
    $('announcement').textContent = 'Error de consulta. Puedes reintentar.';
  } finally { if (request === state.request) loading(false); }
}
function renderHistory() {
  $('area-heading').replaceChildren(document.createTextNode('Superficie'), document.createElement('br'), document.createTextNode('(ha)'));
  const rows = [], buttons = [];
  for (const record of state.rows) {
    const tr = element('tr', 'history-row'); tr.dataset.period = record.period;
    const periodCell = element('td');
    const button = element('button', 'period-button', periodLabel(record.period)); button.type = 'button'; button.addEventListener('click', () => selectPeriod(record.period)); periodCell.append(button);
    const area = element('td', 'numeric', fmt(record.forestHa)); if (record.forestHa == null) area.setAttribute('aria-label', 'Superficie no disponible');
    const change = element('td', `numeric ${record.change.ha < 0 ? 'loss' : record.change.ha > 0 ? 'gain' : ''}`, signed(record.change.ha));
    change.title = `${periodLabel(record.reference)}: ${record.changeReason}`;
    change.append(element('span', 'subvalue', record.change.pct == null ? '—' : `${signed(record.change.pct)} %`));
    const status = element('td'); status.append(badge(record));
    tr.append(periodCell, area, change, status); rows.push(tr);
    const timeline = element('button', record.status === 'sin_registros' ? 'missing' : record.status === 'pendiente_validacion' ? 'pending' : '', periodLabel(record.period));
    timeline.dataset.period = record.period; timeline.setAttribute('aria-label', `${periodLabel(record.period)}: ${badge(record).textContent}`);
    timeline.append(element('small', '', badge(record).textContent)); timeline.addEventListener('click', () => selectPeriod(record.period)); buttons.push(timeline);
  }
  $('history-body').replaceChildren(...rows); $('timeline').replaceChildren(...buttons);
}
function selectPeriod(period) {
  const record = state.rows.find(r => r.period === period); if (!record) return;
  state.selected = period;
  for (const tr of $('history-body').children) { const active = tr.dataset.period === period; tr.classList.toggle('active', active); tr.querySelector('button').setAttribute('aria-pressed', String(active)); }
  for (const button of $('timeline').children) button.setAttribute('aria-current', String(button.dataset.period === period));
  $('detail-title').textContent = `${periodLabel(period)} · ${municipality().name}`;
  $('detail-status').replaceChildren(badge(record));
  const grid = element('div', 'detail-grid');
  const item = (title, value, note) => { const dl = element('dl', 'detail-item'); const dd = element('dd', '', value); if (note) dd.append(element('small', '', note)); dl.append(element('dt', '', title), dd); return dl; };
  grid.append(item(isReference(record) ? 'Bosque cartografiado' : 'Superficie forestal', record.forestHa == null ? 'No disponible' : `${fmt(record.forestHa)} ha`, record.status === 'en_curso' || record.provisional ? `Periodo en curso · corte ${state.snapshot.cutoff}` : isReference(record) ? record.sourceLabel : 'Clasificación CDSE no validada'));
  grid.append(item(isReference(record) ? 'Cambio cartográfico neto' : 'Cambio neto', record.change.ha == null ? 'No disponible' : `${signed(record.change.ha)} ha`, record.change.pct == null ? record.referenceHa === 0 ? 'Porcentaje: base cero' : 'Porcentaje no disponible' : `${signed(record.change.pct)} %`));
  grid.append(item('Periodo de referencia', periodLabel(record.reference), record.referenceHa == null ? 'Superficie no disponible' : `${fmt(record.referenceHa)} ha`));
  const note = element('p', 'detail-note', `${record.reason} ${record.changeReason}`);
  const quality = element('p', 'detail-observation', record.coveragePct != null ? `Cobertura válida por área: ${fmt(record.coveragePct)} %.` : 'Cobertura válida por área: no disponible.');
  if (record.observationPct != null) quality.append(document.createTextNode(` Diagnóstico SCL: ${fmt(record.observationPct)} % de los píxeles observados al menos un día cumple el mínimo temporal. No es porcentaje de bosque, no está ponderado por área y no aplica el margen de nubes de 40 m.`));
  $('detail-content').replaceChildren(grid, note, quality);
  if (isReference(record)) {
    quality.textContent = `Área municipal de la fuente: ${fmt(record.referenceAreaHa)} ha. Cobertura cartográfica: ${fmt(record.mappedCoveragePct)} %. Incluye relleno temporal; no mide disponibilidad de observaciones sin nubes.`;
    const source = element('p', 'detail-observation');
    const link = element('a', '', 'MapBiomas México · Colección 1'); link.href = 'https://mexico.mapbiomas.org/'; link.target = '_blank'; link.rel = 'noopener';
    source.append(link, document.createTextNode(` · Consulta: ${dateText(record.sourceUpdatedAt)}. Límite: ${record.geometryVersion}. El mapa INEGI de esta página sirve para localizar el municipio; tiene un límite diferente.`));
    $('detail-content').append(source);
    const classes = element('p', 'detail-observation', record.forestClasses.map(c => `${c.name}: ${fmt(c.ha)} ha`).join(' · '));
    $('detail-content').append(classes);
  }
  if (local && record.catalogProducts != null) {
    const catalog = element('p', 'detail-catalog');
    catalog.textContent = `Catálogo CDSE: ${record.catalogProducts} productos y ${record.observationDays} días con observaciones. Consultado: ${dateText(record.catalogUpdatedAt)}.`;
    if (record.qualityUpdatedAt) catalog.append(document.createTextNode(` Auditoría SCL: ${dateText(record.qualityUpdatedAt)}${record.qualitySource === 'cache_scl' || record.qualitySource === 'piloto_importado' ? ' (resultado guardado)' : ''}.`));
    $('detail-content').append(catalog);
    if (isReference(record) && record.observationPct != null) $('detail-content').append(element('p', 'detail-observation', `Calidad Sentinel: ${fmt(record.observationPct)} % de los píxeles observados cumple el mínimo temporal SCL. Es un diagnóstico de observaciones, no porcentaje de bosque ni cobertura ponderada por área; no aplica margen espacial de nubes.`));
  }
  updateMap(); $('announcement').textContent = `Mostrando ${periodLabel(period)}.`;
}

// A compact map of the official municipal geometries, in a local equirectangular display.
// Area is never computed from these simplified display paths.
function createMap() {
  const points = [];
  const rings = geometry => geometry.type === 'Polygon' ? geometry.coordinates : geometry.coordinates.flat();
  for (const f of state.features) for (const ring of rings(f.geometry)) points.push(...ring);
  const lons = points.map(p => p[0]), lats = points.map(p => p[1]);
  const minLon = Math.min(...lons), maxLon = Math.max(...lons), minLat = Math.min(...lats), maxLat = Math.max(...lats);
  const cosine = Math.cos((minLat + maxLat) / 2 * Math.PI / 180);
  const width = (maxLon - minLon) * cosine, height = maxLat - minLat;
  const scale = Math.min(660 / width, 570 / height); state.kmPerUnit = 111.32 / scale;
  const project = p => [(p[0] - minLon) * cosine * scale + (760 - width * scale) / 2, (maxLat - p[1]) * scale + (660 - height * scale) / 2];
  const paths = [];
  for (const f of state.features) {
    const m = f.properties; const all = [];
    const d = rings(f.geometry).map(ring => { const projected = ring.map(project); all.push(...projected); return projected.map((p, i) => `${i ? 'L' : 'M'}${p[0].toFixed(2)},${p[1].toFixed(2)}`).join(' ') + 'Z'; }).join(' ');
    const xs = all.map(p => p[0]), ys = all.map(p => p[1]);
    state.bounds.set(m.id, [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)]);
    const path = svgNode('path', { d, class: 'municipality-shape', 'fill-rule': 'evenodd', fill: '#cedacb', role: 'button', tabindex: '0', 'aria-label': `Consultar ${m.name}`, 'data-id': m.id });
    path.addEventListener('click', () => { chooseMunicipality(m.id); query(); });
    path.addEventListener('keydown', e => { if (['Enter', ' '].includes(e.key)) { e.preventDefault(); chooseMunicipality(m.id); query(); } });
    const showTip = () => {
      const rec = state.selected ? getRecord('real', m, state.selected, state.snapshot) : null;
      $('map-tooltip').textContent = `${m.name} · ${isReference(rec) && rec.forestHa != null ? `${fmt(rec.forestHa)} ha cartografiadas · MapBiomas` : rec?.status === 'sin_registros' ? 'Sin datos' : 'Sin estimación disponible'}`;
      $('map-tooltip').hidden = false;
    };
    path.addEventListener('pointerenter', showTip); path.addEventListener('focus', showTip);
    path.addEventListener('pointerleave', () => $('map-tooltip').hidden = true); path.addEventListener('blur', () => $('map-tooltip').hidden = true);
    state.paths.set(m.id, path); paths.push(path);
  }
  $('municipal-shapes').replaceChildren(...paths); updateMap(); updateScale();
}
function color(fraction) { const a = [220,238,196], b = [46,129,86]; return `rgb(${a.map((v, i) => Math.round(v + (b[i] - v) * fraction)).join(',')})`; }
function updateMap() {
  const chosen = municipality();
  const current = state.rows.find(r => r.period === state.selected);
  $('map-title').textContent = chosen?.name || 'Estado de México';
  $('map-kicker').textContent = isReference(current) ? 'CARTOGRAFÍA ANUAL · MAPBIOMAS' : 'VISTA MUNICIPAL · CDSE';
  $('map-subtitle').textContent = state.selected ? `${periodLabel(state.selected)} · ${isReference(current) ? 'Localización municipal · límite INEGI' : 'Sin estimación forestal validada'}` : 'Selecciona un municipio y consulta un periodo';
  for (const m of state.municipalities) {
    const path = state.paths.get(m.id); if (!path) continue;
    const selected = m.id === state.municipality; const record = state.selected ? getRecord('real', m, state.selected, state.snapshot) : null;
    path.classList.toggle('selected', selected); path.setAttribute('aria-pressed', String(selected));
    path.setAttribute('fill', isReference(record) && record.forestHa != null ? color(record.forestHa / record.referenceAreaHa) : selected ? 'url(#pending-pattern)' : '#cedacb');
  }
  const selectedPath = state.paths.get(state.municipality); if (selectedPath) $('municipal-shapes').append(selectedPath);
  const legend = $('legend'); legend.replaceChildren();
  if (isReference(current) && state.selected) {
    legend.append(element('strong', '', 'Bosque cartografiado'), element('div', 'gradient'));
    const ticks = element('div', 'gradient-labels'); ticks.append(element('span', '', '0 %'), element('span', '', '100 %')); legend.append(ticks);
    legend.append(element('span', '', 'Proporción municipal · MapBiomas'));
  } else legend.append(element('strong', '', 'Disponibilidad de resultados'));
  const neutral = element('span'); neutral.append(element('i', 'swatch neutral'), document.createTextNode('Sin resultado disponible'));
  const selected = element('span'); const selectedSwatch = element('i', 'swatch selected');
  const selectedRecord = chosen && state.selected ? getRecord('real', chosen, state.selected, state.snapshot) : null;
  if (isReference(selectedRecord) && selectedRecord.forestHa != null) selectedSwatch.style.background = color(selectedRecord.forestHa / selectedRecord.referenceAreaHa);
  selected.append(selectedSwatch, document.createTextNode('Municipio seleccionado')); legend.append(neutral, selected);
  $('selection-label').replaceChildren();
  if (chosen) {
    const bounds = state.bounds.get(chosen.id);
    if (bounds) {
      const x = (bounds[0] + bounds[2]) / 2, y = (bounds[1] + bounds[3]) / 2;
      const circle = svgNode('circle', { cx:x, cy:y, r:4, fill:'#fff', stroke:'#294f37', 'stroke-width':2, 'vector-effect':'non-scaling-stroke' });
      $('selection-label').append(circle);
    }
  }
}
function setView(view) { state.view = view; $('municipal-map').setAttribute('viewBox', view.join(' ')); updateScale(); }
function zoom(factor) {
  const [x,y,w,h] = state.view; const newWidth = Math.max(30, Math.min(900, w * factor)); const newHeight = newWidth * h / w;
  const bounds = state.bounds.get(state.municipality);
  const cx = bounds ? (bounds[0]+bounds[2])/2 : x+w/2, cy = bounds ? (bounds[1]+bounds[3])/2 : y+h/2;
  setView([cx-newWidth/2, cy-newHeight/2, newWidth, newHeight]);
}
function updateScale() {
  if (!state.kmPerUnit) return;
  const rect = $('municipal-map').getBoundingClientRect(); const pixelsPerUnit = Math.min(rect.width / state.view[2], rect.height / state.view[3]);
  const targetKm = 70 / pixelsPerUnit * state.kmPerUnit;
  const magnitude = 10 ** Math.floor(Math.log10(targetKm)); const rounded = [1,2,5,10].map(n => n * magnitude).filter(n => n <= targetKm).at(-1) || magnitude;
  $('scale-label').textContent = `≈ ${rounded < 1 ? `${Math.round(rounded*1000)} m` : `${rounded} km`}`;
  $('scale-bar').style.width = `${rounded / state.kmPerUnit * pixelsPerUnit}px`;
}

let matches = [], activeOption = -1;
function closeOptions() { $('municipality-options').hidden = true; $('municipality-input').setAttribute('aria-expanded','false'); $('municipality-input').removeAttribute('aria-activedescendant'); }
function showOptions(all = false) {
  matches = state.municipalities.filter(m => all || normalize(m.name).includes(normalize($('municipality-input').value)));
  activeOption = -1; $('municipality-input').removeAttribute('aria-activedescendant');
  $('municipality-options').replaceChildren(...matches.map((m, i) => { const option = element('button','',m.name); option.type='button'; option.id=`municipality-${m.id}`; option.setAttribute('role','option'); option.setAttribute('aria-selected',String(m.id===state.municipality)); option.tabIndex=-1; option.addEventListener('pointerdown',e=>e.preventDefault()); option.addEventListener('click',()=>chooseMunicipality(m.id)); return option; }));
  if (!matches.length) $('municipality-options').append(element('p','','No se encontraron municipios.'));
  $('municipality-options').hidden = false; $('municipality-input').setAttribute('aria-expanded','true');
}
function chooseMunicipality(id) {
  state.municipality=id; $('municipality-input').value=municipality().name; closeOptions(); clearResults();
}
$('municipality-input').addEventListener('focus',()=>showOptions(true));
$('municipality-input').addEventListener('input',()=>{ state.municipality=state.municipalities.find(m=>normalize(m.name)===normalize($('municipality-input').value))?.id || ''; clearResults(); showOptions(); });
$('municipality-input').addEventListener('blur',closeOptions);
$('municipality-input').addEventListener('keydown',e=>{
  if(e.key==='Escape'){closeOptions();return;}
  if(['ArrowDown','ArrowUp'].includes(e.key)){
    e.preventDefault(); if($('municipality-options').hidden) showOptions(true);
    activeOption=Math.max(0,Math.min(matches.length-1,activeOption+(e.key==='ArrowDown'?1:-1)));
    [...$('municipality-options').children].forEach((n,i)=>n.classList.toggle('active',i===activeOption));
    const option=$('municipality-options').children[activeOption]; if(option){$('municipality-input').setAttribute('aria-activedescendant',option.id);option.scrollIntoView({block:'nearest'});}
  }else if(e.key==='Enter'&&!$('municipality-options').hidden){e.preventDefault();if(matches[activeOption])chooseMunicipality(matches[activeOption].id);else if(matches.length===1)chooseMunicipality(matches[0].id);else closeOptions();}
});
for(const id of ['from-period','to-period']) $(id).addEventListener('change',()=>clearResults());
$('query-form').addEventListener('submit',e=>{e.preventDefault();closeOptions();query();});
$('refresh-cdse').addEventListener('click',()=>query({update:true}));
$('zoom-in').addEventListener('click',()=>zoom(.7));$('zoom-out').addEventListener('click',()=>zoom(1/.7));$('reset-map').addEventListener('click',()=>setView([0,0,760,660]));
$('fit-municipality').addEventListener('click',()=>{const b=state.bounds.get(state.municipality);if(b){const w=Math.max(45,(b[2]-b[0])*1.9),h=Math.max(45,(b[3]-b[1])*1.9);setView([(b[0]+b[2]-w)/2,(b[1]+b[3]-h)/2,w,h]);}});
new ResizeObserver(updateScale).observe($('map-stage'));
$('help-button').addEventListener('click',()=>$('help-dialog').showModal());
for(const id of ['close-help','accept-help'])$(id).addEventListener('click',()=>$('help-dialog').close());
async function initialize(){
  $('fatal-error').hidden=true;
  try{
    const [geo,snapshot]=await Promise.all(['./data/municipios.json','./data/piloto.json'].map(async url=>{const response=await fetch(url,{cache:'no-store'});if(!response.ok)throw new Error(`HTTP ${response.status}`);return response.json();}));
    if(geo.features?.length!==125||!Array.isArray(snapshot.records))throw new Error('Datos incompletos');
    state.features=geo.features;state.municipalities=geo.features.map(f=>f.properties).sort((a,b)=>a.name.localeCompare(b.name,'es'));state.snapshot=snapshot;
    if(local){
      state.backend=await api.status();state.snapshot=restrictReferences(state.snapshot,state.backend);
      $('source-cutoff').textContent=`Corte de consulta: ${state.backend.cutoff}. El servidor local consulta CDSE y conserva el historial. La fecha de cada auditoría se muestra en el detalle del periodo.`;
    }
    createMap();populatePeriods();loading(false);await query();
  }catch(error){$('fatal-error').querySelector('span').textContent='No fue posible cargar el catálogo y los datos municipales. Revisa la conexión e intenta de nuevo.';$('fatal-error').hidden=false;$('result-context').textContent='Carga pendiente';}
}
$('reload').addEventListener('click',initialize);initialize();
