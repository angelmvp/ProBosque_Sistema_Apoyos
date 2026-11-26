export const MONTHS = ['Ene–Feb', 'Mar–Abr', 'May–Jun', 'Jul–Ago', 'Sep–Oct', 'Nov–Dic'];
export const normalize = value => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim();
export const isReference = record => record?.source === 'mapbiomas-mexico-collection1-v1';

export function restrictReferences(snapshot, status) {
  const valid = new Set(status.referenceError ? [] : status.referenceMunicipalities || []);
  return { ...snapshot, cutoff: status.cutoff,
    municipalRecords: Object.fromEntries(Object.entries(snapshot.municipalRecords || {}).filter(([id]) => valid.has(id))),
    records: valid.has(snapshot.municipality) ? snapshot.records : snapshot.records.filter(r => !isReference(r)) };
}

export function parsePeriod(value) {
  const match = /^(\d{4})(?:-B([1-6]))?$/.exec(value);
  if (!match || Number(match[1]) < 1900) throw new Error('Periodo no válido.');
  return { year: Number(match[1]), bim: match[2] ? Number(match[2]) : null };
}
export function periodIndex(value) { const p = parsePeriod(value); return p.year * 6 + (p.bim || 1) - 1; }
export function periodLabel(value) { const p = parsePeriod(value); return p.bim ? `${MONTHS[p.bim - 1]} ${p.year}` : `${p.year}`; }
export function previousPeriod(value) {
  const p = parsePeriod(value);
  return p.bim ? (p.bim === 1 ? `${p.year - 1}-B6` : `${p.year}-B${p.bim - 1}`) : `${p.year - 1}`;
}
export function periodStart(value) { const p = parsePeriod(value); return `${p.year}-${String(p.bim ? p.bim * 2 - 1 : 1).padStart(2, '0')}-01`; }
export function isOpen(value, cutoff) {
  const p = parsePeriod(value);
  const next = !p.bim || p.bim === 6 ? `${p.year + 1}-01-01` : `${p.year}-${String(p.bim * 2 + 1).padStart(2, '0')}-01`;
  return periodStart(value) <= cutoff && cutoff < next;
}
export function availablePeriods(frequency, cutoff) {
  const values = [];
  for (let year = 2017; year <= Number(cutoff.slice(0, 4)); year++) {
    for (let b = 1; b <= (frequency === 'bimestral' ? 6 : 1); b++) {
      const value = frequency === 'bimestral' ? `${year}-B${b}` : `${year}`;
      if (periodStart(value) <= cutoff) values.push(value);
    }
  }
  return values;
}
export function validateFilters(filters, municipalities, cutoff) {
  if (!municipalities.some(m => m.id === filters.municipality)) throw new Error('Selecciona un municipio del catálogo.');
  if (!['anual', 'bimestral'].includes(filters.frequency)) throw new Error('Selecciona la frecuencia.');
  const periods = availablePeriods(filters.frequency, cutoff);
  if (!periods.includes(filters.from) || !periods.includes(filters.to)) throw new Error('Selecciona periodos entre 2017 y la fecha de corte.');
  if (periodIndex(filters.from) > periodIndex(filters.to)) throw new Error('El periodo inicial debe ser anterior o igual al final.');
  return periods.slice(periods.indexOf(filters.from), periods.indexOf(filters.to) + 1);
}
export function demoRecord(municipality, period, cutoff) {
  const p = parsePeriod(period);
  if (period === '2023' || period === '2025-B3') return { period, forestHa: null, status: 'sin_registros', simulated: true, reason: 'Ausencia de datos simulada para probar los huecos del historial.' };
  const fraction = Math.max(0, Math.min(.96, .24 + (Number(municipality.id) % 47) / 47 * .47 - (p.year - 2021) * .0032 - ((p.bim || 1) - 1) * .00055));
  return { period, forestHa: Math.round(municipality.areaHa * fraction * 100) / 100,
    status: isOpen(period, cutoff) ? 'en_curso' : 'con_datos', simulated: true, coveragePct: 100,
    reason: 'Cifra ficticia para probar la interfaz. No es una medición satelital.' };
}
export function delta(current, previous, comparable = true) {
  if (!comparable || current == null || previous == null) return { ha: null, pct: null };
  return { ha: current - previous, pct: previous > 0 ? 100 * (current - previous) / previous : null };
}
export function getRecord(mode, municipality, period, snapshot) {
  if (mode === 'demo') return demoRecord(municipality, period, snapshot.cutoff);
  const records = municipality.id === snapshot.municipality ? snapshot.records : snapshot.municipalRecords?.[municipality.id] || [];
  const found = records.find(r => r.period === period && (!r.municipality || r.municipality === municipality.id));
  return found ? { ...found, coveragePct: null } : { period, forestHa: null,
    status: isOpen(period, snapshot.cutoff) ? 'en_curso' : 'sin_registros',
    reason: 'No hay superficies disponibles para este periodo. La cartografía pública disponible es anual y comprende 2017–2025.' };
}
export function buildHistory(mode, filters, municipalities, snapshot) {
  const periods = validateFilters(filters, municipalities, snapshot.cutoff);
  const municipality = municipalities.find(m => m.id === filters.municipality);
  return periods.map(period => {
    const record = getRecord(mode, municipality, period, snapshot);
    const reference = previousPeriod(period);
    const baseline = getRecord(mode, municipality, reference, snapshot);
    const open = isOpen(period, snapshot.cutoff) || isOpen(reference, snapshot.cutoff);
    if (mode !== 'demo' && isReference(record)) {
      const comparable = !open && !parsePeriod(period).bim && isReference(baseline) && record.municipality === baseline.municipality && record.sourceFingerprint === baseline.sourceFingerprint && record.geometryVersion === baseline.geometryVersion;
      const change = delta(record.forestHa, baseline.forestHa, comparable);
      return { ...record, reference, referenceHa: isReference(baseline) ? baseline.forestHa : null, change,
        changeReason: change.ha == null ? 'No hay dos mapas anuales completos, consecutivos y comparables.' : 'Diferencia entre mapas anuales de la misma colección y límite territorial; no confirma deforestación o recuperación. Sin intervalo de confianza local.' };
    }
    return { ...record, reference, referenceHa: baseline.forestHa,
      change: delta(record.forestHa, baseline.forestHa, !open),
      changeReason: open ? 'Periodo en curso: no se compara con periodos completos.' : record.forestHa == null || baseline.forestHa == null ? 'Falta una estimación del periodo actual o del inmediatamente anterior.' : baseline.forestHa === 0 ? 'Porcentaje no calculable: base cero.' : 'Comparación con el periodo inmediatamente anterior.' };
  });
}
