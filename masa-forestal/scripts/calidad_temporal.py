"""Auditoría SCL temporal a 20 m. JSON únicamente; sin estimar bosque.

Guarda cada bloque para reanudar sin repetir procesamiento exitoso.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

from cdse_piloto import ROOT, CATALOG, STATS, CDSEError, SentinelHubClient, load_credentials, pilot_geometry, write_json

sys.path.insert(0, str(ROOT / '.tools/geospatial'))
from pyproj import Transformer
from shapely.geometry import shape, mapping, box
from shapely.ops import transform

OUT = ROOT / 'data/piloto/temporal-20m'
PERIODS = [('2023', '2023-01-01', '2024-01-01', 8),
           ('2024', '2024-01-01', '2025-01-01', 8),
           ('2025', '2025-01-01', '2026-01-01', 8),
           ('2024-B6', '2024-11-01', '2025-01-01', 2),
           ('2025-B1', '2025-01-01', '2025-03-01', 2),
           ('2025-B2', '2025-03-01', '2025-05-01', 2)]


def make_evalscript(start, end, minimum):
    return '''//VERSION=3
const FROM = "%sT00:00:00Z", TO = "%sT00:00:00Z";
const MIN_MONTHS = %d;
function setup() {
  return {input:[{bands:["SCL","dataMask"]}], mosaicking:"ORBIT",
          output:[{id:"temporal",bands:["eligible","validMonths"],sampleType:"FLOAT32"},
                  {id:"dataMask",bands:1}]};
}
function preProcessScenes(c) {
  c.scenes.orbits = c.scenes.orbits.filter(o => o.dateFrom >= FROM && o.dateFrom < TO);
  return c;
}
function evaluatePixel(samples, scenes) {
  let counts = new Array(12).fill(0), observed = 0;
  for (let i=0;i<samples.length;i++) {
    let s=samples[i];
    if (s.dataMask !== 1) continue;
    observed=1;
    if ([4,5,6].includes(s.SCL)) {
      let m=new Date(scenes.orbits[i].dateFrom).getUTCMonth();
      counts[m]++;
    }
  }
  let valid=counts.map(n => n>=2 ? 1:0);
  let n=valid.reduce((a,b)=>a+b,0);
  let quarters=true;
  if (MIN_MONTHS===8) for(let q=0;q<4;q++) {
    if(valid.slice(q*3,q*3+3).reduce((a,b)=>a+b,0)===0) quarters=false;
  }
  return {temporal:[n>=MIN_MONTHS && quarters ? 1:0,n],dataMask:[observed]};
}
''' % (start, end, minimum)


def blocks(geometry):
    # Múltiplos exactos de 20 m, núcleos disjuntos.
    xs, ys = [367060, 383100, 399140], [2109880, 2121680, 2133460]
    result = []
    for iy in range(2):
        for ix in range(2):
            bounds = [xs[ix], ys[iy], xs[ix+1], ys[iy+1]]
            clipped = geometry.intersection(box(*bounds))
            if not clipped.is_empty:
                result.append((f'{iy}-{ix}', bounds, mapping(clipped)))
    return result


def request_for(period, bounds, geometry):
    label, start, end, minimum = period
    return {'input': {'bounds': {'bbox': bounds, 'geometry': geometry,
                     'properties': {'crs': 'http://www.opengis.net/def/crs/EPSG/0/32614'}},
                     'data': [{'type': 'sentinel-2-l2a',
                               'dataFilter': {'maxCloudCoverage': 100, 'mosaickingOrder': 'leastCC'},
                               'processing': {'upsampling': 'NEAREST', 'downsampling': 'NEAREST'}}]},
            'aggregation': {'timeRange': {'from': start+'T00:00:00Z', 'to': end+'T00:00:00Z'},
                            'aggregationInterval': {'of': 'P1Y' if minimum==8 else 'P2M'},
                            'resx':20, 'resy':20, 'evalscript':make_evalscript(start,end,minimum)}}


def summarize(response):
    rows=response.get('data', [])
    if len(rows)!=1 or rows[0].get('error'):
        raise CDSEError('Bloque temporal sin resultado completo.')
    bands=rows[0]['outputs']['temporal']['bands']
    stats=bands['eligible']['stats']
    observed=stats['sampleCount']-stats['noDataCount']
    mean=stats['mean']
    if observed<=0:
        return {'observados':0,'elegibles':0,'meses_validos_media':None}
    if not isinstance(mean,(int,float)) or not 0<=mean<=1:
        raise CDSEError('Media de elegibilidad inválida.')
    eligible=round(observed*mean)
    if abs(eligible-observed*mean)>0.01:
        raise CDSEError('El conteo binario no concuerda con las estadísticas.')
    return {'observados':observed,'elegibles':eligible,
            'meses_validos_media':bands['validMonths']['stats']['mean']}


def catalog_inventory(client):
    path=OUT/'catalogo-autenticado.json'
    payload={'collections':['sentinel-2-l2a'],'intersects':pilot_geometry(),
             'datetime':'2023-01-01T00:00:00Z/2026-01-01T00:00:00Z','limit':100}
    query_hash=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
    if path.exists():
        saved=json.loads(path.read_text(encoding='utf-8'))
        if saved.get('query_hash')==query_hash and saved.get('completo'): return
    rows, seen=[],set()
    for page in range(100):
        result=client.request(CATALOG,payload)
        if result.get('type')!='FeatureCollection': raise CDSEError('Catálogo autenticado inválido.')
        for f in result['features']:
            if '2023-01-01' <= f['properties']['datetime'][:10] < '2026-01-01':
                rows.append({'id':f['id'],'properties':f['properties']})
        cursor=result.get('context',{}).get('next')
        if cursor is None: break
        if str(cursor) in seen: raise CDSEError('Cursor de catálogo repetido.')
        seen.add(str(cursor)); payload['next']=cursor
    else: raise CDSEError('Catálogo autenticado incompleto.')
    write_json(path,{'fecha_utc':datetime.now(timezone.utc).isoformat(),'query_hash':query_hash,
                    'completo':True,'paginas':page+1,'productos':rows})
    print(f'Catálogo autenticado: {len(rows)} registros, {page+1} páginas.',flush=True)


def main():
    client=SentinelHubClient(load_credentials())
    catalog_inventory(client)
    geom=transform(Transformer.from_crs(4326,32614,always_xy=True).transform,shape(pilot_geometry()))
    tiles=blocks(geom)
    summaries=[]
    # Primero bimestres, luego años. Bloques exitosos se reutilizan.
    for period in PERIODS[3:]+PERIODS[:3]:
        partials=[]
        for label,bounds,geometry in tiles:
            payload=request_for(period,bounds,geometry)
            digest=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
            path=OUT/f'{period[0]}_{label}.json'
            cached=json.loads(path.read_text(encoding='utf-8')) if path.exists() else None
            if cached and cached.get('request_hash')==digest:
                response=cached['response']
            else:
                response=client.request(STATS,payload)
                summarize(response)
                write_json(path,{'fecha_utc':datetime.now(timezone.utc).isoformat(),
                                'request_hash':digest,'request':payload,'response':response})
            partials.append(summarize(response))
            print(f'{period[0]} bloque {label}: listo.',flush=True)
        total=sum(r['observados'] for r in partials)
        eligible=sum(r['elegibles'] for r in partials)
        summary={'periodo':period[0],'pixeles_observados_al_menos_un_dia':total,
                 'pixeles_cumplen_minimo_temporal':eligible,
                 'pct_elegible_entre_observados':100*eligible/total if total else None,
                 'superficie_forestal_ha':None,'margen_nubes_40m_aplicado':False,
                 'estado':'calidad_temporal_scl_sin_clasificacion'}
        summaries.append(summary)
        write_json(OUT/'resumen.json',{'completo':len(summaries)==len(PERIODS),
                     'resolucion_m':20,'version':'scl-temporal-v1','periodos':summaries,
                     'limite':'Porcentaje entre píxeles observados en alguna fecha. No mide área forestal '
                              'ni incluye margen espacial de nubes; es un límite optimista de elegibilidad.'})
        print(json.dumps(summary,ensure_ascii=True),flush=True)


if __name__=='__main__':
    try: main()
    except CDSEError as exc:
        print(str(exc),file=sys.stderr)
        raise SystemExit(1)
