"""Carga verificable de la cartografía anual de los 125 municipios del Edomex."""
from datetime import datetime
import hashlib
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from server.cartography import read, validate_statistics, SOURCE, YEARS, LEAVES, FOREST


def verified(directory, evidence, filename, endpoint):
    if evidence['archivo'] != filename or evidence['metodo'] != 'GET' or evidence['http_status'] != 200:
        raise ValueError('Archivo o respuesta no reconocidos.')
    url = urlsplit(evidence['url'])
    if (url.scheme != 'https' or url.hostname != 'prd.plataforma.mapbiomas.org'
            or url.username or url.password or url.path != '/api/v1/mexico' + endpoint):
        raise ValueError('Origen de referencia inesperado.')
    path = directory / filename
    if not path.resolve().is_relative_to(directory.resolve()) or path.is_symlink():
        raise ValueError('Archivo fuera del conjunto autorizado.')
    if hashlib.sha256(path.read_bytes()).hexdigest() != evidence['sha256']:
        raise ValueError('La referencia cambió desde la descarga.')
    if datetime.fromisoformat(evidence['fecha_consulta_utc'].replace('Z', '+00:00')).tzinfo is None:
        raise ValueError('Fecha de consulta sin zona horaria.')
    query = parse_qs(url.query)
    if query.get('tenantId') != ['mapbiomas']:
        raise ValueError('Consulta de otra fuente.')
    return read(path), query


def evidences(items, expected):
    if len(items) != len(expected) or {r['archivo'] for r in items} != set(expected):
        raise ValueError('Procedencia incompleta o duplicada.')
    return {r['archivo']: r for r in items}


def load_state_reference(directory, catalog_path, strict=False):
    directory, catalog_path = Path(directory), Path(catalog_path)
    if not directory.exists():
        return None
    manifest = read(directory / 'manifest.json')
    catalog = read(catalog_path)
    expected = {row['cvegeo'] for row in catalog['municipios']}
    if len(expected) != 125 or any(not c.startswith('15') or len(c) != 5 for c in expected):
        raise ValueError('Catálogo municipal no reconocido.')
    if (manifest.get('version') != 'mapbiomas-mexico-c1-v1-edomex' or manifest.get('completo') is not True
            or manifest.get('catalogo_local_sha256') != hashlib.sha256(catalog_path.read_bytes()).hexdigest()
            or manifest.get('anios') != sorted(YEARS) or set(manifest.get('clases', [])) != LEAVES
            or set(manifest.get('clases_bosque', [])) != FOREST):
        raise ValueError('Conjunto municipal incompleto o de otra versión.')
    shared = evidences(manifest['solicitudes'], ['municipios-listado.json', 'leyenda.json', 'coleccion.json'])
    listing, query = verified(directory, shared['municipios-listado.json'], 'municipios-listado.json', '/territories')
    if query.get('parentId') != ['37-2-15'] or query.get('categoryId') != ['3']:
        raise ValueError('Listado de otra entidad territorial.')
    if listing.get('page') != 1 or listing.get('numberOfPages') != 1 or len(listing.get('territories', [])) != 125:
        raise ValueError('Listado municipal incompleto.')
    index = {item['geocode']: item['id'] for item in listing['territories'] if item.get('categoryId') == 3}
    if set(index) != expected or len(set(index.values())) != 125:
        raise ValueError('Claves municipales ausentes o duplicadas.')
    labels, _ = verified(directory, shared['leyenda.json'], 'leyenda.json', '/legends/by/key/default')
    collection, _ = verified(directory, shared['coleccion.json'], 'coleccion.json', '/themes/subthemes/d3631c59-3724-40b2-8d71-7189933692ef')
    entries = manifest['municipios']
    if len(entries) != 125 or {item['cvegeo'] for item in entries} != expected:
        raise ValueError('El conjunto no corresponde a los 125 municipios.')
    municipalities, errors = {}, {}
    common_fingerprint = ''.join(shared[name]['sha256'] for name in sorted(shared))
    for item in entries:
        code = item['cvegeo']
        try:
            if item.get('estado') != 'completo' or item.get('territory_id') != index[code]:
                raise ValueError('Identidad municipal incorrecta.')
            files = [f'territorios/{code}.json', f'estadisticas/{code}.json']
            evidence = evidences(item['solicitudes'], files)
            territory, _ = verified(directory, evidence[files[0]], files[0], '/territories/' + index[code])
            raw, query = verified(directory, evidence[files[1]], files[1], '/statistics/area')
            if (query.get('territoryId') != [index[code]] or query.get('subthemeKey') != ['coverage_lclu']
                    or query.get('legendKey') != ['default'] or sorted(map(int, query.get('year', []))) != sorted(YEARS)
                    or sorted(map(int, query.get('pixelValue', []))) != sorted(LEAVES)):
                raise ValueError('La consulta no corresponde al municipio o a la serie.')
            rows, error = validate_statistics(raw, labels['legend']['items'], territory['territory'],
                collection['subtheme']['asset'], municipality=code, territory_id=index[code])
            fingerprint = hashlib.sha256((common_fingerprint + ''.join(evidence[name]['sha256'] for name in files)).encode()).hexdigest()
            timestamp = evidence[files[1]]['fecha_consulta_utc']
            for row in rows:
                row.update(sourceUpdatedAt=timestamp, sourceFingerprint=fingerprint)
            municipalities[code] = {'municipality': code, 'records': rows, 'source': SOURCE,
                'maxConservationErrorHa': error, 'technicalChecksPassed': True,
                'forestValidated': False, 'sourceFingerprint': fingerprint}
        except (ValueError, KeyError, TypeError, OSError):
            errors[code] = 'La referencia municipal no pasó las comprobaciones de integridad, identidad o superficie.'
    if strict and errors:
        raise ValueError('Hay referencias municipales incompletas o inválidas: ' + ', '.join(sorted(errors)))
    return {'municipalities': municipalities, 'errors': errors, 'years': sorted(YEARS),
            'source': SOURCE, 'forestValidated': False, 'expectedMunicipalities': 125,
            'manifestFingerprint': hashlib.sha256((directory / 'manifest.json').read_bytes()).hexdigest()}
