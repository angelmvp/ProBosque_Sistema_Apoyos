from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from server.service import ForestService, ROOT, now
from server.municipal_grid import municipal_blocks
from server.operation import RequestControl, LocalLimit, configuration
from server.cdse_adapter import CDSEProvider
from cdse_piloto import CDSEHTTPError, retry_seconds
from shapely.geometry import shape
from shapely.ops import transform, unary_union
from pyproj import Transformer


def params(code='15030', start='2025', end='2025'):
    return {'municipality': code, 'frequency': 'anual', 'from': start, 'to': end}


class MunicipalGridTests(unittest.TestCase):
    def test_provider_resumes_unfinished_blocks_and_rejects_changed_cache(self):
        features=json.loads((ROOT/'data/municipios/municipios-wgs84.geojson').read_text(encoding='utf-8'))['features']
        geometry=next(f['geometry'] for f in features if f['properties']['cvegeo']=='15106')
        tiles=municipal_blocks(geometry)[:2]
        response={'data':[{'outputs':{'temporal':{'bands':{
            'eligible':{'stats':{'sampleCount':100,'noDataCount':10,'mean':.8}},
            'validMonths':{'stats':{'mean':10}}}}}}]}
        class Client:
            calls=0
            def request(self,url,payload):
                self.calls+=1
                if self.calls==2:
                    raise CDSEHTTPError(503,'unavailable')
                return response
        client=Client()
        with tempfile.TemporaryDirectory() as temp, patch('server.cdse_adapter.inventory',return_value={'products':10,'days':10,'fingerprint':'catalog-v1','checkedAt':now()}), patch('server.municipal_grid.municipal_blocks',return_value=tiles):
            provider=CDSEProvider(Path(temp),geometry,client,municipality='15106')
            with self.assertRaises(CDSEHTTPError):
                provider.process('2025',lambda message:None)
            result=provider.process('2025',lambda message:None)
            self.assertEqual(client.calls,3)
            self.assertEqual(result['qualityCachedBlocks'],1)
            self.assertEqual(result['qualityBlocks'],2)
            self.assertEqual(result['observationPct'],80)
            cache=next((Path(temp)/'data/servidor/bloques/15106').rglob('*.json'))
            value=json.loads(cache.read_text(encoding='utf-8'))
            value['response']['data'][0]['outputs']['temporal']['bands']['eligible']['stats']['mean']=.9
            cache.write_text(json.dumps(value),encoding='utf-8')
            provider.process('2025',lambda message:None)
            self.assertEqual(client.calls,4)

    def test_125_municipalities_have_disjoint_aligned_complete_blocks(self):
        features = json.loads((ROOT / 'data/municipios/municipios-wgs84.geojson').read_text(encoding='utf-8'))['features']
        self.assertEqual(len(features), 125)
        project = Transformer.from_crs(4326, 32614, always_xy=True).transform
        for f in features:
            with self.subTest(municipality=f['properties']['cvegeo']):
                parts = municipal_blocks(f['geometry'])
                geometries = [shape(p[2]) for p in parts]
                original = transform(project, shape(f['geometry']))
                union = unary_union(geometries)
                self.assertLess(union.symmetric_difference(original).area, .01)
                self.assertLess(abs(sum(g.area for g in geometries) - union.area), .01)
                for label, bounds, geometry in parts:
                    self.assertTrue(all(v % 20 == 0 for v in bounds))
                    self.assertLessEqual((bounds[2] - bounds[0]) / 20, 800)
                    self.assertLessEqual((bounds[3] - bounds[1]) / 20, 800)


class OperationTests(unittest.TestCase):
    def test_daily_limit_is_persistent_and_includes_retries_without_secrets(self):
        with tempfile.TemporaryDirectory() as temp:
            settings = configuration(ROOT) | {'max_solicitudes_dia': 2}
            path = Path(temp) / 'usage.sqlite3'
            control = RequestControl(path, settings, sleeper=lambda delay: None)
            control.reserve('catalog'); control.reserve('statistics')
            control.response('statistics', {'x-processingunits-spent': '1.25'})
            restored = RequestControl(path, settings, sleeper=lambda delay: None)
            with self.assertRaises(LocalLimit):
                restored.reserve('catalog')
            self.assertEqual(restored.summary()['requests'], 2)
            self.assertEqual(restored.summary()['processingUnitsReported'], 1.25)

    def test_sentinel_retry_after_is_milliseconds_not_seconds(self):
        self.assertAlmostEqual(retry_seconds('3398', 'sh.dataspace.copernicus.eu'), 3.398)
        self.assertEqual(retry_seconds('10', 'identity.dataspace.copernicus.eu'), 10)
        self.assertIsNone(retry_seconds('NaN', 'sh.dataspace.copernicus.eu'))
        self.assertIsNone(retry_seconds('invalid', 'sh.dataspace.copernicus.eu'))

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.calls = []
        outer = self
        class Provider:
            fail = None
            def process(self, period, progress):
                outer.calls.append(period)
                if self.fail:
                    raise self.fail
                return {'period': period, 'forestHa': None, 'status': 'pendiente_validacion',
                    'qualityGridVersion': 'municipal-utm14-20m-v1', 'catalogUpdatedAt': now(),
                    'catalogProducts': 5, 'observationDays': 5, 'observationPct': 90}
        self.provider = Provider()
        self.path = Path(self.temp.name) / 'service.sqlite3'
        self.service = ForestService(database=self.path, provider=self.provider, cutoff=lambda:'2026-11-26', credentials_ready=True, reference_data=False)

    def tearDown(self):
        self.service.close()
        self.temp.cleanup()

    def finish(self, job, desired=('completado','fallido')):
        until = time.monotonic() + 8
        while time.monotonic() < until:
            result = self.service.public_job(job['id'])
            if result['status'] in desired:
                return result
            time.sleep(.02)
        self.fail('El trabajo no terminó.')

    def test_every_municipality_and_closed_annual_period_are_enabled(self):
        status = self.service.status()
        self.assertEqual(len(status['processingMunicipalities']),125)
        self.assertEqual(status['supportedPeriods'],[str(y) for y in range(2017,2026)])
        for code in self.service.municipalities:
            self.assertTrue(self.service.history(params(code))['processingSupported'])
        self.assertFalse(self.service.history(params(start='2026',end='2026'))['processingSupported'])
        result = self.finish(self.service.start(params('15106')))
        self.assertEqual(result['status'],'completado')
        self.assertEqual(self.calls,['2024','2025'])
        self.assertEqual(self.service.record('15106','2025')['catalogProducts'],5)
        self.assertIsNone(self.service.record('15030','2025').get('catalogProducts'))

    def test_other_municipality_never_uses_first_municipality_cached_result(self):
        self.finish(self.service.start(params('15106')))
        self.finish(self.service.start(params('15030')))
        self.assertEqual(self.calls,['2024','2025','2024','2025'])

    def test_finished_period_checkpoint_survives_restart_and_skips_completed_work(self):
        self.service.close()
        stamp = now()
        with self.service.store.connection() as db:
            db.execute('INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?,?,?,?)', ('b'*32,self.service.namespace,'resume-key',json.dumps(params()),'procesando',1,2,'working',None,stamp,stamp))
            db.execute('INSERT INTO job_periods VALUES(?,?,?)', ('b'*32,'2024',stamp))
            db.execute('INSERT INTO records VALUES(?,?,?,?)', (self.service.namespace,'15030','2024',json.dumps({'period':'2024','catalogProducts':4})))
        self.service = ForestService(database=self.path, provider=self.provider, cutoff=lambda:'2026-11-26', credentials_ready=True, reference_data=False)
        result = self.finish({'id':'b'*32})
        self.assertEqual(result['status'],'completado')
        self.assertEqual(result['completed'],2)
        self.assertEqual(self.calls,['2025'])

    def test_temporary_failure_is_scheduled_and_success_resumes_same_job(self):
        self.provider.fail = CDSEHTTPError(429,'PRIVATE_DO_NOT_LEAK',retry_after=.1)
        self.service.operation['espera_reintento_segundos'] = .1
        job = self.service.start(params())
        until = time.monotonic() + 5
        while time.monotonic() < until:
            pending = self.service.public_job(job['id'])
            if pending['attempts']:
                break
            time.sleep(.02)
        self.assertEqual(pending['status'],'pendiente')
        self.assertNotIn('PRIVATE',json.dumps(pending))
        self.assertIsNotNone(pending['nextAttemptAt'])
        self.provider.fail = None
        self.assertEqual(self.finish(job)['status'],'completado')

    def test_recent_diagnostics_are_reused_and_expired_diagnostics_refresh(self):
        self.finish(self.service.start(params()))
        with self.service.store.connection() as db:
            db.execute("UPDATE jobs SET updated_at='2000-01-01'")
        self.finish(self.service.start(params()))
        self.assertEqual(self.calls,['2024','2025'])
        with self.service.store.connection() as db:
            db.execute("UPDATE jobs SET updated_at='2000-01-01'")
        for year in ('2024','2025'):
            row=self.service.store.get_record(self.service.namespace,'15030',year)
            row['catalogUpdatedAt']='2000-01-01T00:00:00+00:00'
            self.service.store.put_record(self.service.namespace,'15030',row)
        self.finish(self.service.start(params()))
        self.assertEqual(self.calls,['2024','2025','2024','2025'])


if __name__ == '__main__':
    unittest.main()
