"""Historial persistente y trabajos CDSE; no publica bosque sin clasificador validado."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
import threading
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from cdse_piloto import CDSEError, CDSEHTTPError, CDSEConnectionError, load_credentials
from server.cartography import load_reference, attach_reference, reference_change, SOURCE
from server.state_reference import load_state_reference
from server.operation import RequestControl, LocalLimit, configuration

VERSION = 'api-local-v2'
PILOT = '15110'
SUPPORTED = ('2023', '2024', '2025', '2024-B6', '2025-B1', '2025-B2')
ACTIVE = ('pendiente', 'procesando')


class ProcessingStopped(Exception):
    pass


def now():
    return datetime.now(timezone.utc).isoformat()


def today():
    return datetime.now(timezone(timedelta(hours=-6))).date().isoformat()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)


class APIError(Exception):
    def __init__(self, status, code, message):
        self.status, self.code = status, code
        super().__init__(message)


class InstanceLock:
    """A second server must not mark the first server's running jobs interrupted."""
    def __init__(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.file = path.open('a+b')
        try:
            self.file.seek(0, 2)
            if self.file.tell() == 0:
                self.file.write(b'0')
                self.file.flush()
            self.file.seek(0)
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.file.close()
            raise APIError(409, 'servidor_en_uso', 'Ya hay un servidor utilizando este historial. Usa la instancia abierta o detenla antes de iniciar otra.') from None

    def close(self):
        self.file.close()


def period_bounds(period):
    if not isinstance(period, str) or not re.fullmatch(r'(?:19|20)\d{2}(?:-B[1-6])?', period):
        raise APIError(422, 'periodo_invalido', 'El periodo debe ser un año o un bimestre natural válido.')
    year = int(period[:4])
    month = int(period[-1]) * 2 - 1 if '-B' in period else 1
    start = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 11 or '-B' not in period else date(year, month + 2, 1)
    return start, end


def previous(period):
    year = int(period[:4])
    if '-B' not in period:
        return str(year - 1)
    b = int(period[-1])
    return f'{year-1}-B6' if b == 1 else f'{year}-B{b-1}'


def validate(params, municipalities, cutoff):
    if not isinstance(params, dict) or set(params) != {'municipality', 'frequency', 'from', 'to'}:
        raise APIError(422, 'campos_invalidos', 'Envía municipio, frecuencia y los dos extremos del periodo.')
    if not isinstance(params['municipality'], str) or params['municipality'] not in municipalities:
        raise APIError(422, 'municipio_invalido', 'Selecciona un municipio del catálogo del Estado de México.')
    if params['frequency'] not in ('anual', 'bimestral'):
        raise APIError(422, 'frecuencia_invalida', 'La frecuencia debe ser anual o bimestral.')
    bim = params['frequency'] == 'bimestral'
    for value in (params['from'], params['to']):
        start, _ = period_bounds(value)
        if ('-B' in value) != bim or start.year < 2017 or start.isoformat() > cutoff:
            raise APIError(422, 'periodo_fuera_rango', 'Selecciona periodos de la misma frecuencia entre 2017 y la fecha de corte.')
    start, _ = period_bounds(params['from'])
    final, _ = period_bounds(params['to'])
    if start > final:
        raise APIError(422, 'rango_invertido', 'El periodo inicial debe ser anterior o igual al final.')
    periods = []
    cursor = start
    while cursor <= final:
        p = f'{cursor.year}-B{(cursor.month+1)//2}' if bim else str(cursor.year)
        periods.append(p)
        cursor = period_bounds(p)[1]
    return periods


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.executescript('''
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS records (
                    namespace TEXT NOT NULL, municipality TEXT NOT NULL, period TEXT NOT NULL,
                    payload TEXT NOT NULL, PRIMARY KEY(namespace, municipality, period));
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY, namespace TEXT NOT NULL, query_key TEXT NOT NULL,
                    params TEXT NOT NULL, status TEXT NOT NULL, completed INTEGER NOT NULL,
                    total INTEGER NOT NULL, message TEXT NOT NULL, error_code TEXT,
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
                CREATE UNIQUE INDEX IF NOT EXISTS active_query ON jobs(namespace, query_key)
                    WHERE status IN ('pendiente','procesando');
                CREATE TABLE IF NOT EXISTS job_periods (job_id TEXT NOT NULL, period TEXT NOT NULL,
                    completed_at TEXT NOT NULL, PRIMARY KEY(job_id,period));
                CREATE TABLE IF NOT EXISTS job_runtime (job_id TEXT PRIMARY KEY, attempts INTEGER NOT NULL DEFAULT 0,
                    next_attempt_at TEXT);
            ''')

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def get_record(self, namespace, municipality, period):
        with self.connection() as db:
            row = db.execute('SELECT payload FROM records WHERE namespace=? AND municipality=? AND period=?',
                             (namespace, municipality, period)).fetchone()
        return json.loads(row['payload']) if row else None

    def put_record(self, namespace, municipality, record, seed=False):
        with self.connection() as db:
            sql = 'INSERT OR IGNORE' if seed else 'INSERT OR REPLACE'
            db.execute(f'{sql} INTO records VALUES(?,?,?,?)', (namespace, municipality, record['period'], encode(record)))

    def get_job(self, job_id):
        with self.connection() as db:
            row = db.execute('SELECT * FROM jobs WHERE id=?', (job_id,)).fetchone()
        if not row:
            raise APIError(404, 'trabajo_no_encontrado', 'No existe ese trabajo.')
        result = dict(row)
        result['params'] = json.loads(result['params'])
        return result

    def update_job(self, job_id, status, completed, message, error_code=None):
        with self.connection() as db:
            db.execute('UPDATE jobs SET status=?,completed=?,message=?,error_code=?,updated_at=? WHERE id=?',
                       (status, completed, message, error_code, now(), job_id))


class ForestService:
    def __init__(self, root=ROOT, database=None, provider=None, cutoff=today, credentials_ready=None, reference_data=None):
        self.root, self.cutoff = Path(root), cutoff
        self.catalog = read_json(self.root / 'data/municipios/catalogo.json')
        self.municipalities = {m['cvegeo']: m for m in self.catalog['municipios']}
        self.method = read_json(self.root / 'config/metodologia-forestal.json')
        self.operation = configuration(self.root)
        geometry_path = self.root / 'data/municipios/municipios-wgs84.geojson'
        if hashlib.sha256(geometry_path.read_bytes()).hexdigest() != read_json(self.root / 'data/municipios/validacion-geoespacial.json')['sha256_wgs84']:
            raise ValueError('El catálogo de geometrías cambió sin validación.')
        self.geometries = {f['properties']['cvegeo']: f['geometry'] for f in read_json(geometry_path)['features']}
        if set(self.geometries) != set(self.municipalities):
            raise ValueError('Las geometrías no corresponden al catálogo municipal.')
        self.geometry = read_json(self.root / 'data/municipios/valle-de-bravo-wgs84.geojson')['features'][0]['geometry']
        # A new method or geometry never silently reads a different version's series.
        self.namespace = hashlib.sha256(encode([VERSION, self.method, self.geometries]).encode()).hexdigest()
        database = Path(database or self.root / 'data/servidor/historial.sqlite3')
        self.instance_lock = InstanceLock(database.with_suffix('.lock'))
        try:
            self.store = Store(database)
        except Exception:
            self.instance_lock.close()
            raise
        self.provider = provider
        self.providers = {}
        self.control = RequestControl(database, self.operation)
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='cdse')
        self.lock = threading.Lock()
        self.stopping = threading.Event()
        self.scheduled = set()
        self.closed = False
        self.credentials_ready = credentials_ready
        self.reference_error = False
        try:
            if reference_data is None:
                self.reference = load_state_reference(self.root / 'data/mapbiomas-edomex', self.root / 'data/municipios/catalogo.json')
                if self.reference is None:
                    self.reference = load_reference(self.root / 'data/piloto/mapbiomas')
            else:
                self.reference = reference_data
        except (ValueError, KeyError, TypeError, OSError):
            self.reference, self.reference_error = None, True
        try:
            self.seed()
            self.recover()
            self.scheduler = threading.Thread(target=self.dispatch_pending, name='cdse-recovery', daemon=True)
            self.scheduler.start()
        except Exception:
            self.close()
            raise

    def ready(self):
        if self.credentials_ready is not None:
            return self.credentials_ready
        try:
            load_credentials(self.root / '.env')
            return True
        except CDSEError:
            return False

    def seed(self):
        # Import the original audit only under its documented method and boundary.
        # Creating a new namespace must not relabel old diagnostics as new evidence.
        method_path = self.root / 'config/metodologia-forestal.json'
        evidence = read_json(self.root / 'data/piloto/validacion/dictamen-validacion-calculo.json')['evidencias_sha256']
        expected_method = next((value for key, value in evidence.items()
                                if key.replace('\\', '/') == 'config/metodologia-forestal.json'), None)
        if hashlib.sha256(method_path.read_bytes()).hexdigest() != expected_method or self.method != read_json(method_path):
            return
        boundaries_path = self.root / 'data/municipios/municipios-wgs84.geojson'
        expected_geometry = read_json(self.root / 'data/municipios/validacion-geoespacial.json')['sha256_wgs84']
        if hashlib.sha256(boundaries_path.read_bytes()).hexdigest() != expected_geometry:
            return
        original_geometry = next(f['geometry'] for f in read_json(boundaries_path)['features'] if f['properties']['cvegeo'] == PILOT)
        if self.geometry != original_geometry:
            return
        summary = read_json(self.root / 'data/piloto/temporal-20m/resumen.json')
        for row in summary['periodos']:
            period = row['periodo']
            dates = [read_json(p)['fecha_utc'] for p in (self.root / 'data/piloto/temporal-20m').glob(f'{period}_*.json')]
            record = {'period': period, 'status': 'pendiente_validacion', 'forestHa': None,
                      'coveragePct': None, 'observationPct': row['pct_elegible_entre_observados'],
                      'reason': 'Clasificación forestal pendiente de validación y cobertura temporal incompleta.',
                      'qualityUpdatedAt': max(dates) if dates else None, 'qualitySource': 'piloto_importado',
                      'updatedAt': now(), 'catalogUpdatedAt': None, 'catalogProducts': None, 'observationDays': None}
            self.store.put_record(self.namespace, PILOT, record, seed=True)

    def status(self):
        regional = bool(self.reference and 'municipalities' in self.reference)
        reference_ids = sorted(self.reference['municipalities']) if regional else [self.reference['municipality']] if self.reference else []
        reference_years = [str(y) for y in self.reference['years'] if y >= 2017] if regional else [r['period'] for r in self.reference['records'] if int(r['period']) >= 2017] if self.reference else []
        return {'version': VERSION, 'mode': 'local', 'cutoff': self.cutoff(),
                'credentialsConfigured': self.ready(), 'forestValidated': False,
                'pilotMunicipality': PILOT, 'supportedPeriods': self.annual_periods(),
                'processingMunicipalities': sorted(self.municipalities),
                'operation': self.operational_status(),
                'geometryVersion': self.catalog['version_geometria'], 'methodVersion': self.method['version'],
                'annualReferenceAvailable': bool(reference_ids), 'referenceError': self.reference_error,
                'referenceYears': reference_years, 'referenceMunicipalities': reference_ids,
                'referenceErrors': sorted(self.reference.get('errors', {})) if self.reference else [],
                'capabilities': {'catalogLive': True, 'qualitySCL': True, 'forestClassification': False,
                                 'publicAnnualCartography': bool(self.reference)}}

    def record(self, municipality, period):
        row = self.store.get_record(self.namespace, municipality, period)
        if row:
            # This service publishes quality diagnostics only. A DB edit cannot enable hectares.
            row['forestHa'], row['coveragePct'] = None, None
        else:
            supported = self.supported(municipality, period)
            row = {'period': period, 'forestHa': None, 'coveragePct': None,
                'status': 'sin_procesar' if supported else 'no_habilitado',
                'reason': 'Aún no se ha procesado este periodo.' if supported else 'Consulta CDSE disponible para años completos desde 2017.'}
        if self.reference and municipality in self.reference.get('errors', {}) and '-B' not in period:
            row.update(status='referencia_invalida', reason=self.reference['errors'][municipality])
            return row
        return attach_reference(row, self.reference, municipality)

    def history(self, params):
        periods = validate(params, self.municipalities, self.cutoff())
        rows = []
        for period in periods:
            row = self.record(params['municipality'], period)
            baseline = previous(period)
            row.update(reference=baseline, referenceHa=None, change={'ha': None, 'pct': None},
                       changeReason='No se calcula cambio sin estimaciones forestales validadas en ambos periodos.',
                       provisional=period_bounds(period)[1].isoformat() > self.cutoff())
            if row.get('source') == SOURCE:
                prior = self.record(params['municipality'], baseline)
                row['change'] = reference_change(row, prior, row['provisional'])
                row['referenceHa'] = prior.get('forestHa') if prior.get('source') == SOURCE else None
                row['changeReason'] = ('Diferencia entre mapas anuales de la misma colección y límite territorial; '
                    'no confirma deforestación o recuperación. Sin intervalo de confianza local.'
                    if row['change']['ha'] is not None else 'No hay dos mapas anuales completos, consecutivos y comparables.')
            rows.append(row)
        return {'municipality': params['municipality'], 'frequency': params['frequency'],
                'cutoff': self.cutoff(), 'rows': rows, 'forestValidated': False,
                'processingSupported': all(self.supported(params['municipality'], p) for p in periods),
                'methodVersion': self.method['version'], 'geometryVersion': self.catalog['version_geometria']}

    def start(self, params):
        periods = validate(params, self.municipalities, self.cutoff())
        if any(not self.supported(params['municipality'], p) for p in periods):
            raise APIError(422, 'periodo_no_habilitado', 'CDSE procesa años completos desde 2017 para los 125 municipios.')
        if not self.ready():
            raise APIError(503, 'credenciales_ausentes', 'Configura las credenciales CDSE en el servidor y vuelve a intentar.')
        work = self.work_periods(params)
        key = hashlib.sha256(encode(params).encode()).hexdigest()
        with self.lock, self.store.connection() as db:
            recent = (datetime.now(timezone.utc) - timedelta(minutes=15)).isoformat()
            prior = db.execute("SELECT id FROM jobs WHERE namespace=? AND query_key=? AND (status IN ('pendiente','procesando') OR (status='completado' AND updated_at>?)) ORDER BY created_at DESC LIMIT 1", (self.namespace, key, recent)).fetchone()
            if prior:
                return self.public_job(prior['id'], reused=True)
            count = db.execute("SELECT COUNT(*) FROM jobs WHERE status IN ('pendiente','procesando')").fetchone()[0]
            if count >= self.operation['max_trabajos_pendientes']:
                raise APIError(429, 'cola_llena', 'Hay varios trabajos pendientes. Espera a que terminen y reintenta.')
            job_id, timestamp = uuid.uuid4().hex, now()
            db.execute('INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                       (job_id, self.namespace, key, encode(params), 'pendiente', 0, len(work),
                        'Consulta CDSE en espera.', None, timestamp, timestamp))
            db.execute('INSERT INTO job_runtime(job_id) VALUES(?)', (job_id,))
        self.submit(job_id)
        return self.public_job(job_id)

    def public_job(self, job_id, reused=False):
        job = self.store.get_job(job_id)
        if job['namespace'] != self.namespace:
            raise APIError(404, 'version_distinta', 'Ese trabajo pertenece a otra versión del método.')
        with self.store.connection() as db:
            runtime = db.execute('SELECT attempts,next_attempt_at FROM job_runtime WHERE job_id=?', (job_id,)).fetchone()
        return {key: job[key] for key in ('id', 'params', 'status', 'completed', 'total', 'message', 'error_code', 'created_at', 'updated_at')} | {
            'reused': reused, 'attempts': runtime['attempts'] if runtime else 0,
            'nextAttemptAt': runtime['next_attempt_at'] if runtime else None}

    def annual_periods(self):
        return [str(year) for year in range(2017, int(self.cutoff()[:4]))]

    def supported(self, municipality, period):
        return municipality in self.municipalities and (period in self.annual_periods()
            or municipality == PILOT and '-B' in period and period in SUPPORTED)

    def work_periods(self, params):
        periods = validate(params, self.municipalities, self.cutoff())
        return list(dict.fromkeys(p for p in [previous(periods[0]), *periods] if self.supported(params['municipality'], p)))

    def operational_status(self):
        with self.store.connection() as db:
            pending = db.execute("SELECT count(*) FROM jobs WHERE namespace=? AND status IN ('pendiente','procesando')", (self.namespace,)).fetchone()[0]
        return {'pendingJobs': pending, 'cacheHours': self.operation['vigencia_diagnostico_horas'],
                'automaticRecovery': True, 'maxRetries': self.operation['max_reintentos_trabajo'],
                'usage': self.control.summary()}

    def recover(self):
        with self.store.connection() as db:
            db.execute("UPDATE jobs SET status='fallido',error_code='version_distinta',message=?,updated_at=? WHERE namespace<>? AND status IN ('pendiente','procesando')",
                ('El método cambió; consulta de nuevo para usar su versión actual.', now(), self.namespace))
            rows = db.execute("SELECT id,params FROM jobs WHERE namespace=? AND status IN ('pendiente','procesando')", (self.namespace,)).fetchall()
            for row in rows:
                try:
                    params = json.loads(row['params'])
                    periods = validate(params, self.municipalities, self.cutoff())
                    if any(not self.supported(params['municipality'], p) for p in periods):
                        raise ValueError('Fuera de alcance')
                except (ValueError, KeyError, TypeError, APIError):
                    db.execute("UPDATE jobs SET status='fallido',error_code='consulta_invalida',message=? WHERE id=?", ('La consulta guardada ya no es válida.', row['id']))
                    continue
                db.execute('INSERT OR IGNORE INTO job_runtime(job_id) VALUES(?)', (row['id'],))
                db.execute("UPDATE jobs SET status='pendiente',message=?,updated_at=? WHERE id=?", ('Trabajo recuperado; se conservan los periodos y bloques ya terminados.', now(), row['id']))

    def submit(self, job_id):
        with self.lock:
            if self.stopping.is_set() or job_id in self.scheduled:
                return
            self.scheduled.add(job_id)
        self.executor.submit(self._run, job_id, None)

    def dispatch_pending(self):
        while not self.stopping.is_set():
            with self.store.connection() as db:
                rows = db.execute("SELECT j.id FROM jobs j LEFT JOIN job_runtime r ON j.id=r.job_id WHERE j.namespace=? AND j.status='pendiente' AND (r.next_attempt_at IS NULL OR r.next_attempt_at<=?) ORDER BY j.created_at LIMIT ?",
                    (self.namespace, now(), self.operation['max_trabajos_pendientes'])).fetchall()
            if self.ready():
                for row in rows:
                    self.submit(row['id'])
            self.stopping.wait(1)

    def get_provider(self, municipality):
        if self.provider is not None:
            return self.provider
        if municipality not in self.providers:
            from server.cdse_adapter import CDSEProvider
            from cdse_piloto import SentinelHubClient
            client = SentinelHubClient(load_credentials(self.root / '.env'), transport=self.control.transport)
            self.providers[municipality] = CDSEProvider(self.root, self.geometries[municipality], client,
                municipality=municipality, block_side=self.operation['lado_bloque_px'])
        return self.providers[municipality]

    def fresh(self, record):
        if not record or not record.get('qualityGridVersion'):
            return False
        try:
            elapsed = datetime.now(timezone.utc) - datetime.fromisoformat(record['catalogUpdatedAt'])
            return timedelta(0) <= elapsed < timedelta(hours=self.operation['vigencia_diagnostico_horas'])
        except (KeyError, TypeError, ValueError):
            return False

    def _run(self, job_id, work):
        completed = 0
        try:
            job = self.store.get_job(job_id)
            municipality = job['params']['municipality']
            work = self.work_periods(job['params'])
            with self.store.connection() as db:
                done = {r[0] for r in db.execute('SELECT period FROM job_periods WHERE job_id=?', (job_id,))}
            completed = len(done.intersection(work))
            for period in work:
                if self.stopping.is_set():
                    raise ProcessingStopped()
                if period in done:
                    continue
                self.store.update_job(job_id, 'procesando', completed, f'Consultando catálogo y calidad SCL: {period}.')
                def progress(message):
                    if self.stopping.is_set():
                        raise ProcessingStopped()
                    self.store.update_job(job_id, 'procesando', completed, message)
                record = self.store.get_record(self.namespace, municipality, period)
                if not self.fresh(record):
                    record = self.get_provider(municipality).process(period, progress)
                record['municipality'] = municipality
                with self.store.connection() as db:
                    db.execute('INSERT OR REPLACE INTO records VALUES(?,?,?,?)', (self.namespace, municipality, period, encode(record)))
                    db.execute('INSERT OR REPLACE INTO job_periods VALUES(?,?,?)', (job_id, period, now()))
                completed += 1
            self.store.update_job(job_id, 'completado', completed, 'Diagnóstico CDSE actualizado. Las superficies de MapBiomas conservan su propia fuente y fecha; la validación forestal de Sentinel se informa por separado.')
            with self.store.connection() as db:
                db.execute('UPDATE job_runtime SET next_attempt_at=NULL WHERE job_id=?', (job_id,))
        except ProcessingStopped:
            self.store.update_job(job_id, 'pendiente', completed, 'Se reanudará al iniciar el servidor; resultados parciales conservados.')
        except Exception as exc:
            if isinstance(exc, CDSEHTTPError):
                code = f'cdse_http_{exc.status}'
                message = {401: 'CDSE rechazó las credenciales.', 403: 'CDSE no autorizó la consulta.', 429: 'CDSE limitó temporalmente las solicitudes. Intenta más tarde.'}.get(exc.status, 'CDSE no pudo completar la consulta. Intenta de nuevo.')
            elif isinstance(exc, LocalLimit):
                code, message = 'limite_local', 'Se alcanzó el límite local diario de solicitudes. Los resultados parciales se conservan.'
            elif isinstance(exc, CDSEError):
                code, message = 'cdse_no_disponible', 'No se pudo completar la consulta CDSE. Revisa la conexión y reintenta.'
            else:
                code, message = 'procesamiento_fallido', 'El procesamiento no pudo completarse. Revisa las dependencias del servidor y reintenta.'
            retryable = isinstance(exc, (LocalLimit, CDSEConnectionError)) or isinstance(exc, CDSEHTTPError) and exc.status in (429, 500, 502, 503, 504)
            with self.store.connection() as db:
                runtime = db.execute('SELECT attempts FROM job_runtime WHERE job_id=?', (job_id,)).fetchone()
                attempts = runtime[0] if runtime else 0
                if retryable and attempts < self.operation['max_reintentos_trabajo']:
                    seconds = max(self.operation['espera_reintento_segundos'] * 2 ** attempts, getattr(exc, 'retry_after', 0) or 0)
                    next_at = datetime.now(timezone.utc) + timedelta(seconds=seconds)
                    if isinstance(exc, LocalLimit):
                        next_at = (datetime.now(timezone.utc) + timedelta(days=1)).replace(hour=0, minute=0, second=5, microsecond=0)
                    db.execute('INSERT OR REPLACE INTO job_runtime VALUES(?,?,?)', (job_id, attempts+1, next_at.isoformat()))
                    db.execute("UPDATE jobs SET status='pendiente',completed=?,message=?,error_code=?,updated_at=? WHERE id=?",
                        (completed, message + ' Reintento automático: ' + next_at.isoformat(), code, now(), job_id))
                else:
                    db.execute("UPDATE jobs SET status='fallido',completed=?,message=?,error_code=?,updated_at=? WHERE id=?", (completed, message, code, now(), job_id))
        finally:
            with self.lock:
                self.scheduled.discard(job_id)

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.stopping.set()
        if hasattr(self, 'scheduler'):
            self.scheduler.join(timeout=3)
        self.executor.shutdown(wait=True)
        self.instance_lock.close()
