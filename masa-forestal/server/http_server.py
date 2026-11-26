"""Servidor exclusivamente local: API JSON y archivos públicos de la interfaz."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
import sys
from urllib.parse import parse_qs, unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from server.service import APIError, ForestService, encode


class LocalServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address, service, static):
        self.service = service
        self.static = Path(static).resolve()
        super().__init__(address, Handler)


class Handler(BaseHTTPRequestHandler):
    server_version = 'MasaForestalLocal/1.0'
    sys_version = ''

    def setup(self):
        super().setup()
        self.connection.settimeout(15)

    def log_message(self, format, *args):
        # Request bodies, query strings, headers and credentials never go to logs.
        pass

    def send_bytes(self, status, data, content_type):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        self.end_headers()
        if self.command != 'HEAD':
            try:
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError):
                pass

    def json_response(self, status, body):
        self.send_bytes(status, encode(body).encode('utf-8'), 'application/json; charset=utf-8')

    def check_origin(self, write=False):
        port = self.server.server_address[1]
        allowed = {f'127.0.0.1:{port}', f'localhost:{port}'}
        host = self.headers.get('Host', '')
        origin = self.headers.get('Origin')
        if host not in allowed or (origin and origin != 'http://' + host) or self.headers.get('Sec-Fetch-Site') == 'cross-site':
            raise APIError(403, 'origen_no_permitido', 'La API solo acepta solicitudes desde la aplicación local.')
        if write and self.headers.get('X-MAF-Request') != '1':
            raise APIError(403, 'solicitud_no_permitida', 'Usa la aplicación local para iniciar el procesamiento.')

    def dispatch(self):
        self.check_origin(write=self.command == 'POST')
        parsed = urlsplit(self.path)
        path = unquote(parsed.path)
        service = self.server.service
        if self.command in ('GET', 'HEAD'):
            if path == '/api/estado':
                return self.json_response(200, service.status())
            if path == '/api/municipios':
                return self.json_response(200, {'municipalities': [{'id': key, 'name': m['nombre']} for key, m in service.municipalities.items()]})
            if path == '/api/historial':
                query = parse_qs(parsed.query, keep_blank_values=True)
                if any(len(v) != 1 for v in query.values()):
                    raise APIError(422, 'parametro_duplicado', 'Cada filtro debe aparecer una sola vez.')
                return self.json_response(200, service.history({key: values[0] for key, values in query.items()}))
            if path.startswith('/api/trabajos/'):
                return self.json_response(200, service.public_job(path.removeprefix('/api/trabajos/')))
            if path == '/runtime.js':
                return self.send_bytes(200, b'window.MAF_RUNTIME = Object.freeze({mode:"local",apiBase:"/api"});\n', 'application/javascript; charset=utf-8')
            if path.startswith('/api/'):
                raise APIError(404, 'ruta_inexistente', 'No existe ese recurso de la API.')
            relative = 'index.html' if path == '/' else path.lstrip('/')
            # Explicit public asset list. No directory listings, symlinks, dotenv or databases.
            allowed = {'index.html', 'styles.css', 'app.js', 'domain.js', 'api-client.js', 'data/municipios.json', 'data/piloto.json'}
            candidate = self.server.static / relative
            if relative not in allowed or candidate.is_symlink() or not candidate.is_file() or not candidate.resolve().is_relative_to(self.server.static):
                raise APIError(404, 'archivo_no_encontrado', 'No existe ese archivo público.')
            mime = 'application/javascript' if candidate.suffix == '.js' else mimetypes.guess_type(str(candidate))[0] or 'application/octet-stream'
            return self.send_bytes(200, candidate.read_bytes(), mime + '; charset=utf-8')
        if self.command == 'POST' and path == '/api/consultas':
            if self.headers.get('Content-Type', '').split(';')[0].strip().lower() != 'application/json':
                raise APIError(415, 'tipo_invalido', 'La solicitud debe usar application/json.')
            length = self.headers.get('Content-Length', '')
            if not length.isdigit() or not 0 < int(length) <= 4096:
                raise APIError(413, 'tamano_invalido', 'La solicitud excede el tamaño permitido o está vacía.')
            try:
                payload = json.loads(self.rfile.read(int(length)))
            except (ValueError, UnicodeError):
                raise APIError(400, 'json_invalido', 'La solicitud no contiene JSON válido.') from None
            job = service.start(payload)
            return self.json_response(200 if job['status'] == 'completado' else 202, job)
        raise APIError(405, 'metodo_no_permitido', 'Método o ruta no permitidos.')

    def handle_request(self):
        try:
            self.dispatch()
        except APIError as exc:
            self.json_response(exc.status, {'error': {'code': exc.code, 'message': str(exc)}})
        except Exception:
            self.json_response(500, {'error': {'code': 'error_interno', 'message': 'El servidor no pudo completar la solicitud.'}})

    do_GET = handle_request
    do_HEAD = handle_request
    do_POST = handle_request
    do_OPTIONS = handle_request


def main():
    parser = argparse.ArgumentParser(description='Masa forestal: servidor local y API CDSE.')
    parser.add_argument('--port', type=int, default=4173)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error('Usa un puerto entre 1024 y 65535.')
    try:
        service = ForestService()
    except APIError as exc:
        parser.exit(1, str(exc) + '\n')
    try:
        server = LocalServer(('127.0.0.1', args.port), service, ROOT / 'web/prototipo/dist')
    except OSError:
        service.close()
        parser.exit(1, f'No se pudo abrir el puerto {args.port}; revisa si hay otra instancia en ejecución.\n')
    print(f'Masa forestal local: http://127.0.0.1:{args.port}/', flush=True)
    print('API disponible. Credenciales: ' + ('configuradas.' if service.ready() else 'pendientes.'), flush=True)
    print('Ctrl+C para detener. Los resultados se guardan en SQLite.', flush=True)
    try:
        server.serve_forever(poll_interval=.2)
    except KeyboardInterrupt:
        print('\nCerrando el servidor; se completarán los trabajos que estén en curso.', flush=True)
    finally:
        server.server_close()
        service.close()


if __name__ == '__main__':
    main()
