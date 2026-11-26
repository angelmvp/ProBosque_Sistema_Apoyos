"""Control local persistente de solicitudes; no registra tokens ni cuerpos OAuth."""
from datetime import datetime, timezone
from contextlib import contextmanager
import json
import sqlite3
import threading
import time

from cdse_piloto import CDSEError, request_json, STATS, CATALOG


class LocalLimit(CDSEError):
    pass


def configuration(root):
    value = json.loads((root / 'config/operacion-local.json').read_text(encoding='utf-8'))
    for key, low, high in [('max_solicitudes_dia', 1, 100000), ('max_trabajos_pendientes', 1, 100),
                           ('max_reintentos_trabajo', 0, 5), ('lado_bloque_px', 1, 1000)]:
        if type(value.get(key)) is not int or not low <= value[key] <= high:
            raise ValueError('Configuración operativa inválida: ' + key)
    for key, low, high in [('intervalo_solicitudes_segundos', .1, 60), ('vigencia_diagnostico_horas', 1, 8760),
                           ('espera_reintento_segundos', 1, 300)]:
        if type(value.get(key)) not in (int, float) or not low <= value[key] <= high:
            raise ValueError('Configuración operativa inválida: ' + key)
    return value


class RequestControl:
    def __init__(self, path, settings, sleeper=time.sleep, monotonic=time.monotonic):
        self.path, self.settings = path, settings
        self.sleep, self.clock = sleeper, monotonic
        self.lock, self.last = threading.Lock(), None
        with self.connection() as db:
            db.execute('CREATE TABLE IF NOT EXISTS api_usage (day TEXT NOT NULL, endpoint TEXT NOT NULL, requests INTEGER NOT NULL, processing_units REAL NOT NULL DEFAULT 0, PRIMARY KEY(day, endpoint))')

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=10)
        try:
            with db:
                yield db
        finally:
            db.close()

    def reserve(self, endpoint):
        with self.lock:
            if self.last is not None:
                delay = self.settings['intervalo_solicitudes_segundos'] - (self.clock() - self.last)
                if delay > 0:
                    self.sleep(delay)
            day = datetime.now(timezone.utc).date().isoformat()
            with self.connection() as db:
                db.execute('BEGIN IMMEDIATE')
                total = db.execute('SELECT COALESCE(SUM(requests),0) FROM api_usage WHERE day=?', (day,)).fetchone()[0]
                if total >= self.settings['max_solicitudes_dia']:
                    raise LocalLimit('Se alcanzó el límite local de solicitudes del día.')
                db.execute('INSERT INTO api_usage(day,endpoint,requests) VALUES(?,?,1) ON CONFLICT(day,endpoint) DO UPDATE SET requests=requests+1', (day, endpoint))
            self.last = self.clock()

    def response(self, endpoint, headers):
        value = headers.get('x-processingunits-spent')
        if value is None:
            return
        import math
        try:
            units = float(value)
        except (TypeError, ValueError):
            return
        if not math.isfinite(units) or units < 0:
            return
        day = datetime.now(timezone.utc).date().isoformat()
        with self.connection() as db:
            db.execute('UPDATE api_usage SET processing_units=processing_units+? WHERE day=? AND endpoint=?', (units, day, endpoint))

    def transport(self, url, payload=None, headers=None, encoded=False):
        endpoint = 'statistics' if url == STATS else 'catalog' if url == CATALOG else 'oauth'
        return request_json(url, payload, headers, encoded,
            on_attempt=lambda: self.reserve(endpoint),
            on_response=lambda response_headers: self.response(endpoint, response_headers))

    def summary(self):
        day = datetime.now(timezone.utc).date().isoformat()
        with self.connection() as db:
            rows = db.execute('SELECT endpoint, requests, processing_units FROM api_usage WHERE day=?', (day,)).fetchall()
        return {'dayUTC': day, 'requests': sum(r[1] for r in rows),
                'processingUnitsReported': sum(r[2] for r in rows),
                'requestLimit': self.settings['max_solicitudes_dia'],
                'note': 'Conteo local; las unidades solo incluyen las cabeceras informadas por CDSE. No representa el saldo de la cuenta.'}
