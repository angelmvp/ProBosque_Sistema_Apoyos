/** Las llamadas a /api/* se reenvían al backend (mismo origen: la cookie de sesión funciona sin CORS). */
const urlBackend = process.env.URL_BACKEND || "http://localhost:8000";

export default {
  async rewrites() {
    return [{ source: "/api/:ruta*", destination: `${urlBackend}/api/:ruta*` }];
  },
};
