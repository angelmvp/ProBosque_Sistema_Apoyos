"""Conexión CDSE e inventario del piloto; solo JSON, sin descargar imágenes.

Comandos: inventario-publico, comprobar-acceso, comprobar-calidad.
Credenciales: variables de entorno o .env local (nunca se imprimen).
"""
import argparse
from collections import defaultdict
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = 'https://stac.dataspace.copernicus.eu/v1/search'
CATALOG = 'https://sh.dataspace.copernicus.eu/catalog/v1/search'
TOKEN = 'https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token'
STATS = 'https://sh.dataspace.copernicus.eu/statistics/v1'
OUTPUT = ROOT / 'data' / 'piloto'


class CDSEError(Exception):
    pass


class CDSEConnectionError(CDSEError):
    pass


class CDSEHTTPError(CDSEError):
    def __init__(self, status, message, retry_after=None):
        self.status, self.retry_after = status, retry_after
        super().__init__(message)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise CDSEError('Redirección rechazada; revisar endpoint oficial.')


def retry_seconds(value, host):
    """Sentinel Hub usa milisegundos; OAuth usa Retry-After HTTP en segundos."""
    try:
        delay = float(value)
        if host == 'sh.dataspace.copernicus.eu':
            delay /= 1000
        import math
        return max(0, delay) if math.isfinite(delay) else None
    except (TypeError, ValueError):
        from email.utils import parsedate_to_datetime
        try:
            return max(0, (parsedate_to_datetime(value) - datetime.now(timezone.utc)).total_seconds())
        except (TypeError, ValueError, OverflowError):
            return None


def request_json(url, payload=None, headers=None, encoded=False, on_attempt=None, on_response=None):
    allowed = {'stac.dataspace.copernicus.eu', 'sh.dataspace.copernicus.eu',
               'identity.dataspace.copernicus.eu'}
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or parsed.hostname not in allowed:
        raise CDSEError('Destino de API no permitido.')
    headers = dict(headers or {})
    headers.setdefault('Accept', 'application/geo+json' if parsed.path in (
        '/v1/search', '/catalog/v1/search') else 'application/json')
    headers['User-Agent'] = 'MasaForestalPiloto/0.1'
    if payload is None:
        body = None
    elif encoded:
        body = urlencode(payload).encode('utf-8')
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
    else:
        body = json.dumps(payload, allow_nan=False).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    opener = build_opener(NoRedirect())
    for attempt in range(3):
        if on_attempt:
            on_attempt()
        try:
            with opener.open(Request(url, data=body, headers=headers), timeout=120) as response:
                if on_response:
                    on_response(response.headers)
                return json.load(response)
        except HTTPError as exc:
            # Nunca incluir cuerpos del servidor ni credenciales en errores.
            retry = retry_seconds(exc.headers.get('Retry-After'), parsed.hostname)
            if exc.code in (429, 500, 502, 503, 504) and attempt < 2 and (retry is None or retry <= 60):
                delay = max(1, retry) if retry is not None else 2 ** (attempt + 1)
                time.sleep(delay)
                continue
            raise CDSEHTTPError(exc.code, f'HTTP {exc.code} en {parsed.hostname}{parsed.path}.', retry) from None
        except (URLError, TimeoutError, OSError):
            if attempt < 2:
                time.sleep(2 ** (attempt + 1))
                continue
            raise CDSEConnectionError(f'No se pudo conectar con {parsed.hostname}.') from None
        except (ValueError, UnicodeError):
            raise CDSEError('La API no devolvió JSON válido.') from None


def load_credentials(path=None, environ=None):
    path = path or ROOT / '.env'
    environ = os.environ if environ is None else environ
    allowed = ('CDSE_CLIENT_ID', 'CDSE_CLIENT_SECRET')
    values = {}
    if path.exists():
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            if not line.strip() or line.lstrip().startswith('#'):
                continue
            key, sep, value = line.partition('=')
            key = key.strip()
            if sep and key in allowed:
                value = value.strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                    value = value[1:-1]
                values[key] = value
    for key in allowed:
        if environ.get(key):
            values[key] = environ[key]
    if not all(values.get(key) for key in allowed):
        raise CDSEError('Faltan CDSE_CLIENT_ID o CDSE_CLIENT_SECRET en .env o en el entorno.')
    return values


class SentinelHubClient:
    def __init__(self, credentials, transport=request_json):
        self.credentials = credentials
        self.transport = transport
        self._token = None
        self._expires = 0

    def headers(self):
        if not self._token or time.monotonic() >= self._expires:
            result = self.transport(TOKEN, {
                'grant_type': 'client_credentials',
                'client_id': self.credentials['CDSE_CLIENT_ID'],
                'client_secret': self.credentials['CDSE_CLIENT_SECRET']
            }, encoded=True)
            if not isinstance(result.get('access_token'), str) or not result['access_token']:
                raise CDSEError('CDSE no devolvió un token de acceso válido.')
            self._token = result['access_token']
            self._expires = time.monotonic() + max(0, float(result.get('expires_in', 60)) - 30)
        return {'Authorization': 'Bearer ' + self._token}

    def request(self, url, payload):
        if url not in (CATALOG, STATS):
            raise CDSEError('No se enviará el token a un endpoint distinto de Sentinel Hub.')
        try:
            return self.transport(url, payload, headers=self.headers())
        except CDSEHTTPError as exc:
            if exc.status != 401:
                raise
            self._expires = 0
            return self.transport(url, payload, headers=self.headers())


def utc(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(timezone.utc)


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2,
                               allow_nan=False) + '\n', encoding='utf-8')
    temp.replace(path)


def pilot_geometry():
    source = ROOT / 'data/municipios/valle-de-bravo-wgs84.geojson'
    return json.loads(source.read_text(encoding='utf-8'))['features'][0]['geometry']


def fetch_public(bbox, transport=request_json):
    query = urlencode({'collections': 'sentinel-2-l2a', 'bbox': ','.join(map(str, bbox)),
                       'datetime': '2023-01-01T00:00:00Z/2026-01-01T00:00:00Z', 'limit': 100})
    url, seen, products = PUBLIC + '?' + query, set(), {}
    pages = 0
    while url:
        if url in seen or pages >= 100:
            raise CDSEError('Paginación repetida o incompleta; no se publica un inventario parcial.')
        parsed = urlsplit(url)
        if (parsed.scheme, parsed.netloc, parsed.path) != (
                'https', 'stac.dataspace.copernicus.eu', '/v1/search'):
            raise CDSEError('El catálogo devolvió un enlace de paginación inesperado.')
        seen.add(url)
        page = transport(url)
        if page.get('type') != 'FeatureCollection' or not isinstance(page.get('features'), list):
            raise CDSEError('Respuesta de catálogo incompleta o inválida.')
        pages += 1
        for feature in page['features']:
            props = feature.get('properties', {})
            if not feature.get('id') or not props.get('datetime') or not feature.get('geometry'):
                raise CDSEError('Un producto carece de identificador, fecha o geometría.')
            if feature.get('collection') != 'sentinel-2-l2a':
                raise CDSEError('Colección de producto inesperada.')
            if not (2023 <= utc(props['datetime']).year <= 2025):
                continue
            products[feature['id']] = feature
        links = [link for link in page.get('links', []) if link.get('rel') == 'next']
        if len(links) > 1 or (links and links[0].get('method', 'GET') != 'GET'):
            raise CDSEError('Paginación no compatible.')
        url = links[0]['href'] if links else None
        print(f'Páginas leídas: {pages}; productos únicos: {len(products)}.', flush=True)
    return list(products.values()), pages


def compact(feature):
    p = feature['properties']
    return {'id': feature['id'], 'fecha': p['datetime'], 'plataforma': p.get('platform'),
            'tesela': p.get('grid:code'), 'nubosidad_tesela_pct': p.get('eo:cloud_cover'),
            'orbita_relativa': p.get('sat:relative_orbit'),
            'version_procesamiento': p.get('processing:version'),
            'fecha_procesamiento': p.get('processing:datetime'), 'geometry': feature['geometry']}


def deduplicate(rows):
    selected = {}
    for row in rows:
        tile = row.get('tesela')
        if not tile:
            match = re.search(r'_T([0-9A-Z]{5})_', row['id'])
            tile = match.group(1) if match else row['id']
        key = (utc(row['fecha']), row.get('plataforma'), tile)
        rank = (tuple(int(n) for n in re.findall(r'\d+', row.get('version_procesamiento') or '')),
                row.get('fecha_procesamiento') or '', row['id'])
        if key not in selected or rank > selected[key][0]:
            selected[key] = (rank, row)
    return sorted([value[1] for value in selected.values()], key=lambda r: (r['fecha'], r['id']))


def period_rows(days):
    rows = []
    for year in (2023, 2024, 2025):
        for bimonth in (None, 1, 2, 3, 4, 5, 6):
            months = list(range(1, 13)) if bimonth is None else [2*bimonth-1, 2*bimonth]
            matching = [d for d in days if utc(d['fecha'] + 'T00:00:00Z').year == year
                        and int(d['fecha'][5:7]) in months]
            rows.append({'periodo': str(year) if bimonth is None else f'{year}-B{bimonth}',
                         'frecuencia': 'anual' if bimonth is None else 'bimestral',
                         'dias_con_productos': len(matching),
                         'productos_seleccionados': sum(d['productos'] for d in matching),
                         'dias_por_mes': {f'{year}-{m:02}': sum(int(d['fecha'][5:7]) == m for d in matching)
                                          for m in months},
                         'max_cobertura_geometrica_pct': max((d['cobertura_geometrica_pct'] for d in matching), default=None),
                         'superficie_forestal_ha': None,
                         'calidad_pixeles_verificada': False})
    return rows


def inventory():
    sys.path.insert(0, str(ROOT / '.tools/geospatial'))
    from shapely.geometry import shape
    from shapely.ops import transform, unary_union
    from pyproj import Transformer
    municipality = shape(pilot_geometry())
    projector = Transformer.from_crs(4326, 6933, always_xy=True).transform
    area_geom = transform(projector, municipality)
    products, pages = fetch_public(municipality.bounds)
    relevant = []
    for f in products:
        footprint = shape(f['geometry'])
        if not footprint.is_valid:
            raise CDSEError('Huella de producto inválida; requiere revisión antes de resumir.')
        if footprint.intersection(municipality).area > 0:
            relevant.append(compact(f))
    selected = deduplicate(relevant)
    grouped = defaultdict(list)
    for row in selected:
        grouped[utc(row['fecha']).date().isoformat()].append(row)
    days = []
    for date, members in sorted(grouped.items()):
        union = unary_union([shape(row['geometry']) for row in members])
        covered = transform(projector, union.intersection(municipality)).area
        clouds = [row['nubosidad_tesela_pct'] for row in members if isinstance(row['nubosidad_tesela_pct'], (int, float))]
        days.append({'fecha': date, 'productos': len(members),
                     'cobertura_geometrica_pct': min(100, 100 * covered / area_geom.area),
                     'nubosidad_tesela_min_pct': min(clouds) if clouds else None,
                     'nubosidad_tesela_max_pct': max(clouds) if clouds else None,
                     'ids': [row['id'] for row in members]})
    candidates = sorted([d for d in days if d['fecha'].startswith('2025-01') or d['fecha'].startswith('2025-02')],
                        key=lambda d: (-round(d['cobertura_geometrica_pct'], 4),
                                       d['nubosidad_tesela_max_pct'] if d['nubosidad_tesela_max_pct'] is not None else 101,
                                       d['fecha']))[:5]
    report = {'fecha_consulta_utc': datetime.now(timezone.utc).isoformat(),
              'fuente': PUBLIC, 'cvegeo': '15110', 'intervalo': '[2023-01-01,2026-01-01)',
              'paginacion_completa': True, 'paginas': pages,
              'productos_en_bbox': len(products), 'productos_intersectan_municipio': len(relevant),
              'productos_tras_deduplicar': len(selected), 'dias_distintos': len(days),
              'acceso_sentinel_hub_autenticado': 'no_comprobado_en_este_inventario',
              'nota': 'Inventario del STAC público de CDSE. Las huellas no miden píxeles libres de nubes. '
                      'La disponibilidad en Sentinel Hub se comprueba por separado. No hay estimaciones forestales.',
              'periodos': period_rows(days), 'dias': days, 'candidatos_prueba_b1_2025': candidates}
    write_json(OUTPUT / 'inventario-productos-publicos.json',
               {'fuente': PUBLIC, 'productos': relevant, 'ids_seleccionados': [r['id'] for r in selected]})
    write_json(OUTPUT / 'disponibilidad-publica.json', report)
    print(json.dumps({k: report[k] for k in ('productos_tras_deduplicar', 'dias_distintos', 'paginas')}, ensure_ascii=True))


def check_access():
    client = SentinelHubClient(load_credentials())
    result = client.request(CATALOG, {'collections': ['sentinel-2-l2a'],
                            'intersects': pilot_geometry(),
                            'datetime': '2025-01-01T00:00:00Z/2025-02-28T23:59:59Z', 'limit': 5})
    if result.get('type') != 'FeatureCollection':
        raise CDSEError('Respuesta autenticada de catálogo inesperada.')
    report = {'fecha_prueba_utc': datetime.now(timezone.utc).isoformat(),
              'oauth_correcto': True, 'catalogo_sentinel_hub_accesible': True,
              'consulta_muestra_no_inventario_completo': True,
              'productos_muestra': [{'id': f['id'], 'fecha': f['properties'].get('datetime')}
                                    for f in result['features']],
              'procesamiento_comprobado': False}
    write_json(OUTPUT / 'conexion-cdse.json', report)
    print('Autenticación y consulta de muestra de Sentinel Hub verificadas. No se guardó el token.')


def quality_request(date, geometry):
    begin = datetime.strptime(date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
    end = begin + timedelta(days=1)
    evalscript = '''//VERSION=3
function setup() {
  return {input: [{bands: ["SCL", "dataMask"]}],
          output: [{id: "utilizable", bands: 1, sampleType: "FLOAT32"},
                   {id: "dataMask", bands: 1}]};
}
function evaluatePixel(s) {
  return {utilizable: [[4, 5, 6].includes(s.SCL) ? 1 : 0], dataMask: [s.dataMask]};
}
'''
    return {'input': {'bounds': {'geometry': geometry,
                                'properties': {'crs': 'http://www.opengis.net/def/crs/EPSG/0/32614'}},
                      'data': [{'type': 'sentinel-2-l2a',
                                'dataFilter': {'mosaickingOrder': 'leastCC', 'maxCloudCoverage': 100},
                                'processing': {'upsampling': 'NEAREST', 'downsampling': 'NEAREST'}}]},
            'aggregation': {'timeRange': {'from': begin.strftime('%Y-%m-%dT%H:%M:%SZ'),
                                         'to': end.strftime('%Y-%m-%dT%H:%M:%SZ')},
                            'aggregationInterval': {'of': 'P1D'},
                            'resx': 100, 'resy': 100, 'evalscript': evalscript}}


def summarize_quality(response):
    if not response.get('data') or response.get('error'):
        raise CDSEError('No hay resultados estadísticos utilizables para esta prueba.')
    summaries = []
    for row in response['data']:
        if row.get('error'):
            raise CDSEError('CDSE informó un error dentro del intervalo estadístico.')
        try:
            stats = row['outputs']['utilizable']['bands']['B0']['stats']
            observed = stats['sampleCount'] - stats['noDataCount']
            mean = stats['mean']
        except (KeyError, TypeError):
            raise CDSEError('Respuesta estadística incompleta.') from None
        if observed <= 0:
            fraction = None
        elif not isinstance(mean, (int, float)) or not 0 <= mean <= 1:
            raise CDSEError('Media de la máscara fuera de rango.')
        else:
            fraction = mean * 100
        summaries.append({'intervalo': row.get('interval'), 'pixeles_observados_muestra': observed,
                          'pct_scl_utilizable_entre_pixeles_observados': fraction})
    return summaries


def check_quality(date=None):
    if date is None:
        path = OUTPUT / 'disponibilidad-publica.json'
        if not path.exists():
            raise CDSEError('Ejecuta el inventario público o indica --fecha AAAA-MM-DD.')
        candidates = json.loads(path.read_text(encoding='utf-8'))['candidatos_prueba_b1_2025']
        if not candidates:
            raise CDSEError('No hay una fecha candidata para la prueba.')
        date = candidates[0]['fecha']
    try:
        datetime.strptime(date, '%Y-%m-%d')
    except ValueError:
        raise CDSEError('La fecha debe tener formato AAAA-MM-DD.') from None
    sys.path.insert(0, str(ROOT / '.tools/geospatial'))
    from pyproj import Transformer
    from shapely.geometry import shape, mapping
    from shapely.ops import transform
    projected = transform(Transformer.from_crs(4326, 32614, always_xy=True).transform,
                          shape(pilot_geometry()))
    payload = quality_request(date, mapping(projected))
    client = SentinelHubClient(load_credentials())
    response = client.request(STATS, payload)
    intervals = summarize_quality(response)
    report = {'fecha_prueba_utc': datetime.now(timezone.utc).isoformat(),
              'fecha_observacion': date, 'endpoint': STATS, 'resolucion_m_prueba': 100,
              'procesamiento_estadistico_accesible': True, 'intervalos': intervals,
              'nota': 'Prueba numérica de SCL entre píxeles observados, sin margen de nubes. '
                      'No mide cobertura válida total del municipio, no valida composiciones '
                      'a 20 m y no estima bosque. No se descargaron imágenes.'}
    write_json(OUTPUT / 'prueba-calidad-solicitud.json', payload)
    write_json(OUTPUT / 'prueba-calidad-respuesta.json', response)
    write_json(OUTPUT / 'prueba-calidad.json', report)
    print(json.dumps(report, ensure_ascii=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('accion', choices=['inventario-publico', 'comprobar-acceso', 'comprobar-calidad'])
    parser.add_argument('--fecha', help='Día UTC para la prueba estadística, AAAA-MM-DD.')
    args = parser.parse_args()
    try:
        if args.accion == 'inventario-publico':
            inventory()
        elif args.accion == 'comprobar-acceso':
            check_access()
        else:
            check_quality(args.fecha)
    except CDSEError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
