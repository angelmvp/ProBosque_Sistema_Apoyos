export class ServiceError extends Error {
  constructor(message, code = 'conexion') { super(message); this.name = 'ServiceError'; this.code = code; }
}

export function delay(ms, signal) {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) { reject(new DOMException('Solicitud cancelada', 'AbortError')); return; }
    const abort = () => { clearTimeout(timer); reject(new DOMException('Solicitud cancelada', 'AbortError')); };
    const timer = setTimeout(() => { signal?.removeEventListener('abort', abort); resolve(); }, ms);
    signal?.addEventListener('abort', abort, { once: true });
  });
}

export function createApiClient({ fetcher = fetch, wait = delay, interval = 1000 } = {}) {
  async function request(path, { signal, body } = {}) {
    let response;
    const timeout = new AbortController();
    const onAbort = () => timeout.abort();
    if (signal?.aborted) throw new DOMException('Solicitud cancelada', 'AbortError');
    signal?.addEventListener('abort', onAbort, { once: true });
    const timer = setTimeout(() => timeout.abort(), 20000);
    try {
      response = await fetcher(`/api/${path}`, { method: body ? 'POST' : 'GET', signal: timeout.signal,
        cache: 'no-store', headers: body ? { 'Content-Type': 'application/json', 'X-MAF-Request': '1' } : {},
        ...(body ? { body: JSON.stringify(body) } : {}) });
      const data = await response.json();
      if (!response.ok) throw new ServiceError(data.error?.message || 'El servidor no pudo completar la solicitud.', data.error?.code);
      return data;
    } catch (error) {
      if (signal?.aborted) throw new DOMException('Solicitud cancelada', 'AbortError');
      if (error instanceof ServiceError) throw error;
      throw new ServiceError('No se pudo contactar con el servidor local. Comprueba que está iniciado y reintenta.');
    } finally { clearTimeout(timer); signal?.removeEventListener('abort', onAbort); }
  }
  const history = async (params, signal) => {
    const result = await request(`historial?${new URLSearchParams(params)}`, { signal });
    if (!Array.isArray(result.rows) || !result.rows.length || result.municipality !== params.municipality) throw new ServiceError('El servidor devolvió un historial incompleto.', 'respuesta_invalida');
    return result;
  };
  return {
    status: () => request('estado'),
    history,
    async update(params, { signal, onProgress = () => {} } = {}) {
      let job = await request('consultas', { signal, body: params });
      for (let attempt = 0; attempt < 900; attempt++) {
        if (signal?.aborted) throw new DOMException('Solicitud cancelada', 'AbortError');
        if (!/^[a-f0-9]{32}$/.test(job.id) || !['pendiente', 'procesando', 'completado', 'fallido'].includes(job.status)) throw new ServiceError('El servidor devolvió un trabajo inválido.', 'respuesta_invalida');
        onProgress(job);
        if (job.status === 'fallido') throw new ServiceError(job.message, job.error_code);
        if (job.status === 'completado') return history(params, signal);
        await wait(interval, signal);
        job = await request(`trabajos/${job.id}`, { signal });
      }
      throw new ServiceError('El trabajo sigue en el servidor. Pulsa Actualizar CDSE para retomar su seguimiento.', 'tiempo_de_espera');
    }
  };
}
