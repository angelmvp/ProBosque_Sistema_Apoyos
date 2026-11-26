"""Catálogo y calidad SCL municipales, con caché por geometría, método y adquisición."""
import hashlib
import json
from pathlib import Path

from server.service import ROOT, encode, now, period_bounds, read_json
from cdse_piloto import CATALOG, STATS, CDSEError, SentinelHubClient, load_credentials, utc, write_json, compact, deduplicate


def inventory(client, geometry, period):
    start, end = period_bounds(period)
    # Catalog intervals are inclusive; filter [start,end) so adjacent periods
    # never count the same acquisition at the next period's midnight.
    end_inclusive = end.isoformat() + 'T00:00:00Z'
    payload = {'collections': ['sentinel-2-l2a'], 'intersects': geometry,
               'datetime': f'{start.isoformat()}T00:00:00Z/{end_inclusive}', 'limit': 100}
    rows, seen, identifiers = [], set(), set()
    for _ in range(30):
        page = client.request(CATALOG, payload)
        if page.get('type') != 'FeatureCollection' or not isinstance(page.get('features'), list):
            raise CDSEError('Respuesta de catálogo incompleta.')
        for feature in page['features']:
            if feature.get('collection') != 'sentinel-2-l2a' or not feature.get('id') or not feature.get('geometry') or not feature.get('properties', {}).get('datetime'):
                raise CDSEError('Metadatos de producto incompletos.')
            moment = utc(feature['properties']['datetime']).date()
            if start <= moment < end and feature['id'] not in identifiers:
                identifiers.add(feature['id'])
                rows.append(compact(feature))
        context = page.get('context')
        if not isinstance(context, dict):
            raise CDSEError('Catálogo sin contexto de paginación.')
        cursor = context.get('next')
        if cursor is None:
            break
        if not isinstance(cursor, (int, str)) or str(cursor) in seen:
            raise CDSEError('Paginación repetida o inválida.')
        seen.add(str(cursor))
        payload['next'] = cursor
    else:
        raise CDSEError('Se alcanzó el límite de páginas sin completar el catálogo.')
    unique = deduplicate(rows)
    return {'products': len(unique), 'days': len({utc(r['fecha']).date() for r in unique}),
            'fingerprint': hashlib.sha256(encode([(r['id'], r['fecha']) for r in unique]).encode()).hexdigest(),
            'checkedAt': now()}


class CDSEProvider:
    def __init__(self, root=ROOT, geometry=None, client=None, municipality='15110', block_side=800):
        self.root = Path(root)
        self.geometry = geometry
        self.municipality, self.block_side = municipality, block_side
        self.geometry_hash = hashlib.sha256(encode(geometry).encode()).hexdigest()
        self.client = client or SentinelHubClient(load_credentials(self.root / '.env'))

    def legacy_fingerprint(self, period):
        path = self.root / 'data/piloto/temporal-20m/catalogo-autenticado.json'
        if not path.exists():
            return None
        saved = read_json(path)
        if not saved.get('completo'):
            return None
        start, end = period_bounds(period)
        rows = [compact(dict(f, geometry={})) for f in saved['productos']
                if start <= utc(f['properties']['datetime']).date() < end]
        unique = deduplicate(rows)
        return hashlib.sha256(encode([(r['id'], r['fecha']) for r in unique]).encode()).hexdigest()

    def process(self, period, progress):
        catalog = inventory(self.client, self.geometry, period)
        if not catalog['products']:
            return {'period': period, 'forestHa': None, 'coveragePct': None,
                    'status': 'sin_registros', 'observationPct': None,
                    'catalogProducts': 0, 'observationDays': 0, 'catalogUpdatedAt': catalog['checkedAt'],
                    'updatedAt': now(), 'reason': 'El catálogo autenticado no devolvió escenas para este periodo. No significa cero hectáreas de bosque.'}
        # Lazy import: the web server and cached history work even when GIS deps are missing.
        from calidad_temporal import request_for, summarize
        from server.municipal_grid import municipal_blocks, GRID_VERSION
        tiles = municipal_blocks(self.geometry, side=self.block_side)
        start, end = period_bounds(period)
        spec = (period, start.isoformat(), end.isoformat(), 2 if '-B' in period else 8)
        partials, dates, reused = [], [], 0
        for label, bounds, clipped in tiles:
            progress(f'{self.municipality} · {period}: calidad SCL, bloque {len(partials)+1} de {len(tiles)}.')
            # Shapely mappings contain tuples; normalize to the exact JSON form
            # stored on disk so a resumed block compares equal after decoding.
            payload = json.loads(encode(request_for(spec, bounds, clipped)))
            digest = hashlib.sha256(encode(payload).encode()).hexdigest()
            # Existing audit hashes use json.dumps defaults, not the public encoder.
            digest_legacy = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
            cache = self.root / 'data/servidor/bloques' / self.municipality / self.geometry_hash / f'{period}_{label}.json'
            saved = None
            for candidate in (cache,):
                if candidate.exists():
                    try:
                        value = read_json(candidate)
                    except (ValueError, OSError):
                        continue
                    compatible = value.get('request_hash') in (digest, digest_legacy) and value.get('request') == payload
                    # Imported audits must match their full authenticated inventory.
                    # Keep their original date, even after checking today's catalogue.
                    fingerprint = value.get('catalog_fingerprint')
                    same_catalog = fingerprint == catalog['fingerprint']
                    if compatible and same_catalog:
                        if value.get('response_hash') != hashlib.sha256(encode(value.get('response')).encode()).hexdigest():
                            continue
                        summarize(value['response'])
                        saved = value
                        break
            if saved is None:
                response = self.client.request(STATS, payload)
                summarize(response)
                saved = {'fecha_utc': now(), 'request_hash': digest, 'request': payload,
                         'response': response, 'catalog_fingerprint': catalog['fingerprint'],
                         'response_hash': hashlib.sha256(encode(response).encode()).hexdigest(),
                         'municipality': self.municipality, 'geometry_hash': self.geometry_hash, 'gridVersion': GRID_VERSION}
                write_json(cache, saved)
            else:
                reused += 1
            partials.append(summarize(saved['response']))
            dates.append(saved['fecha_utc'])
        observed = sum(r['observados'] for r in partials)
        eligible = sum(r['elegibles'] for r in partials)
        return {'period': period, 'municipality': self.municipality, 'forestHa': None, 'coveragePct': None,
                'status': 'pendiente_validacion', 'observationPct': 100*eligible/observed if observed else None,
                'qualityUpdatedAt': min(dates), 'qualityUpdatedThrough': max(dates),
                'qualitySource': 'cache_scl' if reused == len(partials) else 'cdse_scl',
                'qualityCachedBlocks': reused, 'qualityBlocks': len(partials),
                'qualityGridVersion': GRID_VERSION, 'qualityGeometryHash': self.geometry_hash,
                'catalogProducts': catalog['products'], 'observationDays': catalog['days'],
                'catalogUpdatedAt': catalog['checkedAt'], 'updatedAt': now(),
                'reason': 'Catálogo CDSE consultado y calidad SCL revisada. Clasificación forestal pendiente de validación; no se estima el total municipal.'}
