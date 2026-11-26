"""Verifica cartografía pública anual sin certificar exactitud ni crear bimestres."""
from copy import deepcopy
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

SOURCE = 'mapbiomas-mexico-collection1-v1'
TERRITORY = '37-3-684'
MUNICIPALITY = '15110'
FOREST = {88, 89, 3, 5}
LEAVES = {88, 89, 3, 5, 66, 45, 11, 15, 36, 19, 9, 21, 24, 25, 33, 34, 27}
YEARS = set(range(2016, 2026))
FILES = {'estadisticas-15110-2016-2025.json', 'leyenda.json', 'municipio.json',
         'municipio-busqueda.json', 'coleccion.json'}
ASSET = 'projects/mapbiomas-public/assets/mexico/lulc/collection1/mapbiomas_mexico_collection1_coverage_v1'
SOURCE_URL = 'https://mexico.mapbiomas.org/'
REASON = ('Superficie cartografiada por MapBiomas México, Colección 1 (Landsat, 30 m). '
          'Incluye bosque templado, tropical seco, tropical húmedo y manglar; excluye cultivos y plantaciones. '
          'La fuente aplica relleno y filtros temporales. Su exactitud local no está validada.')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError('Superficie no finita, negativa o de tipo inválido.')
    return float(value)


def validate_statistics(data, labels, territory, collection, *, municipality=MUNICIPALITY, territory_id=TERRITORY):
    """Comprueba identidad, clases disjuntas, años, unidades y conservación de área."""
    if data.get('unit') != 'ha' or data.get('statMethod') != 'sum':
        raise ValueError('Las estadísticas deben estar en hectáreas y usar suma.')
    if (territory.get('id') != territory_id or territory.get('geocode') != municipality
            or territory.get('parent', {}).get('geocode') != '15'
            or territory.get('category', {}).get('version') != '1'):
        raise ValueError('Territorio o versión municipal inesperados.')
    if collection.get('assetId') != ASSET or collection.get('scale') != 30 or collection.get('version') != 'v1':
        raise ValueError('Colección cartográfica no reconocida.')
    if not YEARS <= set(collection.get('years', [])):
        raise ValueError('Años ausentes en la colección.')
    forest_group = [item for item in labels if item['pixelValue'] == 1]
    if len(forest_group) != 1 or {item['pixelValue'] for item in forest_group[0].get('children', [])} != FOREST:
        raise ValueError('La definición de bosque cambió; se requiere revisión.')
    leaves = [child for item in labels for child in (item.get('children') or [item])]
    if len(leaves) != len(LEAVES) or {item['pixelValue'] for item in leaves} != LEAVES:
        raise ValueError('Leyenda incompleta o duplicada.')
    names = {item['pixelValue']: item['name']['es-ES'] for item in leaves}
    total = number(data['territoryAreaHa'])
    if total <= 0:
        raise ValueError('El municipio debe tener superficie positiva.')
    records, errors = [], []
    for row in data['statistic']:
        year = row.get('year')
        if not isinstance(year, list) or len(year) != 1 or type(year[0]) is not int or year[0] not in YEARS:
            raise ValueError('Periodo cartográfico inválido o agregado.')
        codes = [item['pixelValue'] for item in row['items']]
        if any(type(code) is not int for code in codes) or len(codes) != len(LEAVES) or set(codes) != LEAVES:
            raise ValueError('Clases incompletas, duplicadas o agregadas.')
        areas = {item['pixelValue']: number(item['value']) for item in row['items']}
        declared = number(row['total'])
        error = max(abs(math.fsum(areas.values()) - declared), abs(declared - total))
        if error > 0.01:
            raise ValueError('Las clases no conservan la superficie municipal.')
        errors.append(error)
        observed = math.fsum(areas[code] for code in FOREST)
        missing = areas[27]
        records.append({'period': str(year[0]), 'municipality': municipality, 'forestHa': observed if missing == 0 else None,
                        'observedForestHa': observed, 'unmappedHa': missing,
                        'mappedCoveragePct': 100 * (total - missing) / total,
                        'referenceAreaHa': total, 'forestClasses': [
                            {'code': code, 'name': names[code], 'ha': areas[code]} for code in sorted(FOREST)],
                        'status': 'cartografia_publica' if missing == 0 else 'cartografia_parcial',
                        'source': SOURCE, 'sourceUrl': SOURCE_URL,
                        'sourceLabel': 'MapBiomas México · Colección 1',
                        'geometryVersion': 'MapBiomas POLITICAL_LEVEL_3 v1 · año no informado',
                        'methodVersion': SOURCE, 'forestValidated': False,
                        'confidenceIntervalHa': None, 'temporalGapfill': True,
                        'reason': REASON, 'coveragePct': None})
    if len(records) != len(YEARS) or {int(row['period']) for row in records} != YEARS:
        raise ValueError('Serie anual incompleta o con años duplicados.')
    return sorted(records, key=lambda row: row['period']), max(errors)


def load_reference(directory):
    directory = Path(directory)
    if not directory.exists():
        return None
    metadata = read(directory / 'procedencia.json')
    requests = metadata['solicitudes']
    if len(requests) != len(FILES) or {r['archivo'] for r in requests} != FILES:
        raise ValueError('Procedencia incompleta o archivos no permitidos.')
    for request in requests:
        path = directory / request['archivo']
        url = urlsplit(request['url'])
        if (request['metodo'] != 'GET' or request['http_status'] != 200 or url.scheme != 'https'
                or url.hostname != 'prd.plataforma.mapbiomas.org' or url.username or url.password
                or not url.path.startswith('/api/v1/mexico/')):
            raise ValueError('Origen de la referencia no reconocido.')
        if hashlib.sha256(path.read_bytes()).hexdigest() != request['sha256']:
            raise ValueError('Archivo de referencia modificado desde su consulta.')
    request = next(r for r in requests if r['archivo'].startswith('estadisticas-'))
    query = parse_qs(urlsplit(request['url']).query)
    if (query.get('territoryId') != [TERRITORY] or query.get('subthemeKey') != ['coverage_lclu']
            or query.get('legendKey') != ['default'] or query.get('tenantId') != ['mapbiomas']
            or sorted(map(int, query.get('pixelValue', []))) != sorted(LEAVES)
            or sorted(map(int, query.get('year', []))) != sorted(YEARS)):
        raise ValueError('La consulta no corresponde a la serie y clases esperadas.')
    timestamp = request['fecha_consulta_utc']
    if datetime.fromisoformat(timestamp.replace('Z', '+00:00')).tzinfo is None:
        raise ValueError('La consulta debe tener fecha con zona horaria.')
    collection = read(directory / 'coleccion.json')['subtheme']['asset']
    rows, error = validate_statistics(read(directory / request['archivo']),
        read(directory / 'leyenda.json')['legend']['items'],
        read(directory / 'municipio.json')['territory'], collection)
    fingerprint = hashlib.sha256(''.join(r['sha256'] for r in sorted(requests, key=lambda r: r['archivo'])).encode()).hexdigest()
    for row in rows:
        row.update(sourceUpdatedAt=timestamp, sourceFingerprint=fingerprint)
    return {'municipality': MUNICIPALITY, 'records': rows, 'source': SOURCE,
            'checkedAt': timestamp, 'maxConservationErrorHa': error,
            'technicalChecksPassed': True, 'forestValidated': False,
            'sourceAccuracyPublished': False, 'bimonthlyValidated': False,
            'sourceFingerprint': fingerprint}


def attach_reference(record, bundle, municipality):
    if bundle and 'municipalities' in bundle:
        bundle = bundle['municipalities'].get(municipality)
    if not bundle or municipality != bundle['municipality']:
        return record
    reference = next((r for r in bundle['records'] if r['period'] == record['period']), None)
    return record | deepcopy(reference) if reference else record


def reference_change(current, previous, open_period=False):
    """Solo diferencias entre mapas consecutivos, completos y del mismo origen."""
    empty = {'ha': None, 'pct': None}
    if (open_period or current.get('source') != SOURCE or previous.get('source') != SOURCE
            or current.get('municipality') != previous.get('municipality')
            or current.get('sourceFingerprint') != previous.get('sourceFingerprint')
            or current.get('geometryVersion') != previous.get('geometryVersion')
            or '-B' in current['period'] or '-B' in previous['period']
            or int(current['period']) - int(previous['period']) != 1
            or current.get('forestHa') is None or previous.get('forestHa') is None):
        return empty
    difference = current['forestHa'] - previous['forestHa']
    return {'ha': difference, 'pct': 100 * difference / previous['forestHa'] if previous['forestHa'] > 0 else None}
