/** Cliente HTTP mínimo. Todas las rutas son relativas (/api/...) y la cookie de sesión viaja sola. */

export class ErrorApi extends Error {
  constructor(public estado: number, public codigo: string, mensaje: string) {
    super(mensaje);
  }
}

async function procesar<T>(respuesta: Response): Promise<T> {
  if (respuesta.status === 204) return undefined as T;
  const cuerpo = await respuesta.json().catch(() => null);
  if (!respuesta.ok) {
    const mensaje = cuerpo?.mensaje ?? (typeof cuerpo?.detail === "string" ? cuerpo.detail : "Ocurrió un error inesperado.");
    throw new ErrorApi(respuesta.status, cuerpo?.codigo ?? "error", mensaje);
  }
  return cuerpo as T;
}

export const api = {
  obtener: <T,>(ruta: string) => fetch(ruta, { credentials: "same-origin" }).then((r) => procesar<T>(r)),
  enviarJson: <T,>(ruta: string, datos: unknown, metodo = "POST") =>
    fetch(ruta, { method: metodo, credentials: "same-origin", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(datos) }).then((r) => procesar<T>(r)),
  enviarFormulario: <T,>(ruta: string, datos: FormData, metodo = "POST") =>
    fetch(ruta, { method: metodo, credentials: "same-origin", body: datos }).then((r) => procesar<T>(r)),
  accion: <T = void,>(ruta: string, metodo = "POST") =>
    fetch(ruta, { method: metodo, credentials: "same-origin" }).then((r) => procesar<T>(r)),
};
