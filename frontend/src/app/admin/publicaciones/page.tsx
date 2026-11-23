"use client";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { api } from "@/compartido/api";
import { ETIQUETA_ESTADO, fechaCorta } from "@/compartido/formato";
import { ProtegidaPorSesion } from "@/compartido/ProtegidaPorSesion";
import type { PublicacionAdmin } from "@/compartido/tipos";

function Contenido() {
  const [filas, setFilas] = useState<PublicacionAdmin[] | null>(null);
  const [error, setError] = useState("");
  const cargar = useCallback(() => {
    api.obtener<PublicacionAdmin[]>("/api/publicaciones").then(setFilas).catch((e: Error) => setError(e.message));
  }, []);
  useEffect(() => { cargar(); }, [cargar]);

  async function accion(ruta: string, metodo: string, confirmar?: string) {
    if (confirmar && !window.confirm(confirmar)) return;
    try { await api.accion(ruta, metodo); setError(""); cargar(); } catch (e) { setError((e as Error).message); }
  }

  return (
    <>
      <h1>Publicaciones</h1>
      <p><Link className="boton" href="/admin/publicaciones/nueva">Nueva publicación</Link></p>
      {error && <div className="error">{error}</div>}
      {filas?.length === 0 && <div className="aviso">Todavía no hay publicaciones.</div>}
      {!!filas?.length && (
        <table>
          <thead><tr><th>Programa</th><th>Título</th><th>Archivos</th><th>Vigencia</th><th>Estado</th><th>Acciones</th></tr></thead>
          <tbody>{filas.map((p) => (
            <tr key={p.id}>
              <td>{p.programa_nombre}</td><td>{p.titulo}</td>
              <td>{p.archivos.length}</td>
              <td>{fechaCorta(p.vigencia_inicio)} – {fechaCorta(p.vigencia_fin)}</td>
              <td><span className={`etiqueta ${p.estado}`}>{ETIQUETA_ESTADO[p.estado] ?? p.estado}</span></td>
              <td className="acciones">
                {p.url_pdf && <a href={p.url_pdf} target="_blank" rel="noreferrer">PDF</a>}
                {p.estado === "borrador" && (<>
                  <Link href={`/admin/publicaciones/${p.id}`}>Editar</Link>
                  <button className="boton" onClick={() => accion(`/api/publicaciones/${p.id}/publicar`, "POST", "Una vez publicada ya no se puede modificar ni despublicar. ¿Publicar?")}>Publicar</button>
                  <button className="boton peligro" onClick={() => accion(`/api/publicaciones/${p.id}`, "DELETE", "¿Eliminar este borrador?")}>Eliminar</button>
                </>)}
              </td>
            </tr>))}
          </tbody>
        </table>
      )}
    </>
  );
}

export default function PaginaPublicaciones() {
  return <ProtegidaPorSesion permiso="publicaciones.gestionar"><Contenido /></ProtegidaPorSesion>;
}
