from concurrent.futures import ThreadPoolExecutor
from datetime import date
from http.client import HTTPConnection
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from server.service import APIError, ForestService, Store, validate, previous, period_bounds
from server.http_server import LocalServer
from server.cdse_adapter import inventory, CDSEProvider
from cdse_piloto import CDSEError, CDSEHTTPError


def params(start='2025-B1', end='2025-B1', frequency='bimestral', municipality='15110'):
    return {'municipality': municipality, 'frequency': frequency, 'from': start, 'to': end}


class FakeProvider:
    def __init__(self):
        self.calls = []
        self.error = None
        self.gate = None

    def process(self, period, progress):
        self.calls.append(period)
        if self.gate:
            self.gate.wait(timeout=3)
        if self.error:
            raise self.error
        return {'period': period, 'forestHa': None, 'coveragePct': None, 'status': 'pendiente_validacion',
                'observationPct': 95, 'catalogProducts': 12, 'observationDays': 10,
                'catalogUpdatedAt': '2026-11-26T10:00:00+00:00', 'reason': 'Prueba sintética.'}


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.database = Path(self.temp.name) / 'history.sqlite3'
        self.provider = FakeProvider()
        self.service = ForestService(database=self.database, provider=self.provider,
                                     cutoff=lambda: '2026-11-26', credentials_ready=True, reference_data=False)

    def tearDown(self):
        if self.provider.gate:
            self.provider.gate.set()
        self.service.close()
        self.temp.cleanup()

    def finish(self, job):
        end = time.monotonic() + 5
        while time.monotonic() < end:
            state = self.service.public_job(job['id'])
            if state['status'] not in ('pendiente', 'procesando'):
                return state
            time.sleep(.01)
        self.fail('El trabajo no terminó.')

    def test_calendar_and_immediate_reference(self):
        self.assertEqual(validate(params('2024-B6', '2025-B2'), self.service.municipalities, '2026-11-26'), ['2024-B6', '2025-B1', '2025-B2'])
        self.assertEqual(previous('2025-B1'), '2024-B6')
        self.assertEqual(period_bounds('2024-B1')[1], date(2024, 3, 1))

    def test_validation_rejects_bad_inputs_before_cdse(self):
        for values in [params('2025-B2','2025-B1'),params('2027-B1','2027-B1'),params(municipality='99999'),params(frequency='mensual'),params('2025','2025'),params('2025-B7','2025-B7'),params('2016-B1','2016-B1'),params()|{'unexpected':'x'},params()|{'from':None},params()|{'municipality':[]}]:
            with self.subTest(values=values), self.assertRaises(APIError):
                self.service.start(values)
        self.assertEqual(self.provider.calls, [])

    def test_all_125_municipalities_are_known_but_only_pilot_processes(self):
        self.assertEqual(len(self.service.municipalities), 125)
        rows = self.service.history(params(municipality='15106'))['rows']
        self.assertEqual(rows[0]['status'], 'no_habilitado')
        with self.assertRaises(APIError):
            self.service.start(params(municipality='15106'))
        self.assertEqual(self.provider.calls, [])

    def test_imported_quality_is_never_forest_area(self):
        result = self.service.history(params('2024','2025','anual'))
        self.assertEqual(len(result['rows']), 2)
        self.assertFalse(result['forestValidated'])
        for row in result['rows']:
            self.assertIsNone(row['forestHa'])
            self.assertIsNone(row['coveragePct'])
            self.assertEqual(row['change'], {'ha':None,'pct':None})
            self.assertEqual(row['status'], 'pendiente_validacion')
        self.assertEqual(result['rows'][0]['observationPct'], 88.95501961377181)

    def test_database_cannot_enable_unvalidated_hectares(self):
        row = self.service.record('15110','2025') | {'forestHa':123,'coveragePct':100}
        self.service.store.put_record(self.service.namespace,'15110',row)
        self.assertIsNone(self.service.history(params('2025','2025','anual'))['rows'][0]['forestHa'])

    def test_job_processes_reference_outside_query_and_persists(self):
        job = self.finish(self.service.start(params()))
        self.assertEqual(job['status'], 'completado')
        self.assertEqual(job['completed'], 2)
        self.assertEqual(self.provider.calls, ['2024-B6','2025-B1'])
        row = self.service.history(params())['rows'][0]
        self.assertEqual(row['catalogProducts'], 12)
        self.assertEqual(row['reference'], '2024-B6')
        self.service.close()
        self.service = ForestService(database=self.database, provider=self.provider, cutoff=lambda:'2026-11-26', credentials_ready=True)
        self.assertEqual(self.service.history(params())['rows'][0]['catalogProducts'],12)

    def test_duplicate_requests_share_one_active_job_and_reuse_recent_success(self):
        self.provider.gate = threading.Event()
        with ThreadPoolExecutor(max_workers=4) as pool:
            jobs = list(pool.map(lambda _:self.service.start(params()), range(4)))
        self.assertEqual(len({j['id'] for j in jobs}),1)
        self.provider.gate.set()
        self.finish(jobs[0])
        cached = self.service.start(params())
        self.assertTrue(cached['reused'])
        self.assertEqual(cached['id'], jobs[0]['id'])
        self.assertEqual(self.provider.calls,['2024-B6','2025-B1'])

    def test_provider_failure_is_not_no_data_or_secret_disclosure_and_retries(self):
        self.provider.error=CDSEHTTPError(401,'SECRET_BEARER_DO_NOT_LEAK')
        failed=self.finish(self.service.start(params()))
        self.assertEqual(failed['status'],'fallido')
        self.assertEqual(failed['error_code'],'cdse_http_401')
        self.assertNotIn('SECRET',json.dumps(failed))
        self.assertEqual(self.service.history(params())['rows'][0]['status'],'pendiente_validacion')
        self.provider.error=None
        retried=self.finish(self.service.start(params()))
        self.assertEqual(retried['status'],'completado')
        self.assertNotEqual(retried['id'],failed['id'])

    def test_unexpected_failure_is_sanitized(self):
        self.provider.error=RuntimeError('password=SENSITIVE_TOKEN')
        failed=self.finish(self.service.start(params()))
        self.assertEqual(failed['error_code'],'procesamiento_fallido')
        self.assertNotIn('SENSITIVE',json.dumps(failed))

    def test_missing_credentials_still_allows_saved_history(self):
        self.service.credentials_ready=False
        self.assertFalse(self.service.status()['credentialsConfigured'])
        self.assertEqual(len(self.service.history(params())['rows']),1)
        with self.assertRaises(APIError) as error:
            self.service.start(params())
        self.assertEqual(error.exception.code,'credenciales_ausentes')

    def test_second_instance_cannot_interrupt_active_jobs(self):
        self.provider.gate=threading.Event()
        job=self.service.start(params())
        with self.assertRaises(APIError) as error:
            ForestService(database=self.database,credentials_ready=True)
        self.assertEqual(error.exception.code,'servidor_en_uso')
        self.assertIn(self.service.public_job(job['id'])['status'],('pendiente','procesando'))
        self.provider.gate.set()
        self.assertEqual(self.finish(job)['status'],'completado')

    def test_open_period_not_enabled_or_compared(self):
        row=self.service.history(params('2026','2026','anual'))['rows'][0]
        self.assertTrue(row['provisional'])
        self.assertEqual(row['status'],'no_habilitado')
        self.assertIsNone(row['change']['ha'])

    def test_old_namespace_is_never_mixed_with_current(self):
        self.service.store.put_record('old-method','15110',{'period':'2025','forestHa':99999})
        self.assertIsNone(self.service.history(params('2025','2025','anual'))['rows'][0]['forestHa'])

    def test_changed_method_does_not_relabel_original_audit(self):
        self.service.namespace='changed-version'
        self.service.method=dict(self.service.method,version='another-method')
        self.service.seed()
        self.assertIsNone(self.service.store.get_record('changed-version','15110','2025'))

    def test_interrupted_job_is_recoverable_after_restart(self):
        self.service.close()
        with self.service.store.connection() as db:
            db.execute('INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?,?,?,?)', ('a'*32,self.service.namespace,'interrupted',json.dumps(params()),'procesando',0,2,'working',None,'2026-11-26','2026-11-26'))
        self.service=ForestService(database=self.database,provider=self.provider,credentials_ready=True)
        recovered=self.finish(self.service.public_job('a'*32))
        self.assertEqual(recovered['status'],'completado')
        self.assertEqual(recovered['completed'],2)


class CatalogTests(unittest.TestCase):
    @staticmethod
    def feature(identifier, timestamp):
        return {'id':identifier,'collection':'sentinel-2-l2a','geometry':{'type':'Polygon','coordinates':[]},
                'properties':{'datetime':timestamp,'platform':'sentinel-2a','grid:code':'14QLG'}}

    def test_full_pagination_deduplication_and_exclusive_boundary(self):
        features=[self.feature('one','2025-01-01T10:00:00Z'),self.feature('two','2025-02-28T10:00:00Z')]
        pages=[{'type':'FeatureCollection','features':[features[0]],'context':{'next':1}},
               {'type':'FeatureCollection','features':[features[0],features[1],self.feature('next','2025-03-01T00:00:00Z')],'context':{}}]
        class Client:
            def request(self,url,payload):return pages.pop(0)
        result=inventory(Client(),{},'2025-B1')
        self.assertEqual(result['products'],2)
        self.assertEqual(result['days'],2)

    def test_invalid_pagination_never_publishes_partial_catalog(self):
        class Client:
            def request(self,url,payload):return {'type':'FeatureCollection','features':[],'context':{'next':1}}
        with self.assertRaises(CDSEError):inventory(Client(),{},'2025-B1')

    def test_missing_collection_metadata_or_context_fails(self):
        for page in [{'type':'FeatureCollection','features':[]}, {'type':'FeatureCollection','features':[{'id':'bad'}],'context':{}}]:
            class Client:
                def request(self,url,payload):return page
            with self.subTest(page=page),self.assertRaises(CDSEError):inventory(Client(),{},'2025-B1')

    def test_zero_products_is_missing_surface_not_zero_forest(self):
        class Client:
            def request(self,url,payload):return {'type':'FeatureCollection','features':[],'context':{}}
        record=CDSEProvider(ROOT,{},Client()).process('2025-B1',lambda msg:None)
        self.assertEqual(record['status'],'sin_registros')
        self.assertEqual(record['catalogProducts'],0)
        self.assertIsNone(record['forestHa'])


class HTTPTests(unittest.TestCase):
    finish = ServiceTests.finish

    def setUp(self):
        ServiceTests.setUp(self)
        self.http=LocalServer(('127.0.0.1',0),self.service,ROOT/'web/prototipo/dist')
        self.thread=threading.Thread(target=self.http.serve_forever,kwargs={'poll_interval':.02},daemon=True)
        self.thread.start()

    def tearDown(self):
        self.http.shutdown();self.http.server_close();self.thread.join()
        ServiceTests.tearDown(self)

    def call(self,path,method='GET',body=None,headers=None):
        conn=HTTPConnection('127.0.0.1',self.http.server_address[1],timeout=3)
        conn.request(method,path,body=body,headers=headers or {})
        response=conn.getresponse();result=(response.status,response.read(),dict(response.getheaders()));conn.close()
        return result

    def test_http_serves_page_runtime_and_real_history(self):
        self.assertEqual(self.call('/')[0],200)
        self.assertIn(b'mode:"local"',self.call('/runtime.js')[1])
        status,body,_=self.call('/api/historial?municipality=15110&frequency=bimestral&from=2025-B1&to=2025-B1')
        self.assertEqual(status,200);self.assertIsNone(json.loads(body)['rows'][0]['forestHa'])

    def test_http_does_not_serve_secrets_database_or_paths_outside_dist(self):
        for path in ['/.env','/../.env','/%2e%2e/.env','/data/servidor/historial.sqlite3','/.git/config','/server/service.py','/data/']:
            with self.subTest(path=path):self.assertEqual(self.call(path)[0],404)

    def test_http_rejects_cross_origin_and_dns_rebinding(self):
        self.assertEqual(self.call('/api/estado',headers={'Host':'attacker.invalid'})[0],403)
        self.assertEqual(self.call('/api/estado',headers={'Origin':'https://attacker.invalid'})[0],403)
        self.assertEqual(self.call('/api/consultas','POST',json.dumps(params()),{'Content-Type':'application/json'})[0],403)

    def test_http_job_lifecycle_and_invalid_json(self):
        headers={'Content-Type':'application/json','X-MAF-Request':'1'}
        status,body,_=self.call('/api/consultas','POST',json.dumps(params()),headers)
        self.assertEqual(status,202)
        job=json.loads(body);self.finish(job)
        self.assertEqual(json.loads(self.call('/api/trabajos/'+job['id'])[1])['status'],'completado')
        self.assertEqual(self.call('/api/consultas','POST','{broken',headers)[0],400)
        self.assertEqual(self.call('/api/historial?municipality=15110&municipality=15106')[0],422)


if __name__=='__main__':
    unittest.main()
