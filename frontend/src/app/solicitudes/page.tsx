"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/compartido/api";
import type { Solicitud } from "@/compartido/tipos";
import { ProtegidaPorSesion } from "@/compartido/ProtegidaPorSesion";

function Contenido() {
  const [solicitudes, setSolicitudes] = useState<Solicitud[]>([]);
  const [error, setError] = useState("");
  useEffect(() => {
    api.obtener<Solicitud[]>("/api/solicitudes").then(setSolicitudes).catch((e) => setError(e.message));
  }, []);
  return (
    <div className="sprint2-page solicitudes-page">
      <div className="encabezado-pagina">
        <div><p className="eyebrow">SOLICITUDES DE APOYO</p><h1>Mis solicitudes</h1></div>
        <Link className="boton" href="/solicitudes/nueva">Nueva solicitud</Link>
      </div>
      {error && <p className="alerta">{error}</p>}
      {!solicitudes.length && !error && <p className="s2-vacio">Aún no tienes solicitudes. Inicia una nueva para comenzar.</p>}
      {!!solicitudes.length && <div className="s2-tabla-contenedor">
        <table className="s2-tabla">
          <thead><tr><th>Programa</th><th>Municipio</th><th>Estado</th><th>Fecha de envío</th><th>Folio</th><th>Acciones</th></tr></thead>
          <tbody>{solicitudes.map((solicitud) => (
            <tr key={solicitud.id}>
              <td>{solicitud.programa}</td>
              <td>{solicitud.municipio}</td>
              <td><span className={`s2-etiqueta ${solicitud.estado === "recibida" ? "s2-exito" : solicitud.estado === "borrador" ? "s2-aviso" : solicitud.estado === "con_faltantes" ? "s2-error" : "s2-neutro"}`}>
                {solicitud.estado.replace("_", " ")}
              </span></td>
              <td>{solicitud.enviada_en ? new Date(solicitud.enviada_en).toLocaleDateString("es-MX") : "—"}</td>
              <td>{solicitud.folio ?? "—"}</td>
              <td><div className="acciones">
                <Link href={solicitud.estado === "borrador" ? `/solicitudes/${solicitud.id}/paso/1` : `/solicitudes/${solicitud.id}/confirmacion`}>
                  {solicitud.estado === "borrador" ? "Continuar" : "Ver"}
                </Link>
                {solicitud.acuse_disponible && <a href={`/api/solicitudes/${solicitud.id}/acuse`}>Descargar acuse</a>}
              </div></td>
            </tr>
          ))}</tbody>
        </table>
      </div>}
    </div>
  );
}

export default function PaginaSolicitudes() {
  return <ProtegidaPorSesion><Contenido /></ProtegidaPorSesion>;
}
