"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/compartido/api";
import type { Solicitud } from "@/compartido/tipos";
import { ProtegidaPorSesion } from "@/compartido/ProtegidaPorSesion";

function Contenido() {
  const { id } = useParams<{ id: string }>();
  const [solicitud, setSolicitud] = useState<Solicitud | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.obtener<Solicitud>(`/api/solicitudes/${id}`).then(setSolicitud).catch((e) => setError(e.message));
  }, [id]);

  if (!solicitud) return <div className="sprint2-page"><p>{error || "Cargando acuse…"}</p></div>;
  const recibida = solicitud.estado === "recibida";
  return (
    <div className="sprint2-page s2-confirmacion">
      <p className="eyebrow">HU-07 · Rol: persona solicitante</p>
      <article className="s2-tarjeta-acuse">
        <span className="s2-etiqueta s2-exito">Solicitud enviada</span>
        <h1>Acuse de recepción</h1>
        <p className="nota">Folio asignado</p>
        <strong className="s2-folio">
          {solicitud.folio ?? "Se asignará cuando la Delegación reciba tu solicitud"}
        </strong>
        <dl className="s2-datos-acuse">
          <div><dt>Programa</dt><dd>{solicitud.programa}</dd></div>
          <div><dt>Solicitante</dt><dd>{solicitud.nombre_solicitante}</dd></div>
          <div><dt>Fecha de envío</dt><dd>{solicitud.enviada_en ? new Date(solicitud.enviada_en).toLocaleString("es-MX") : "—"}</dd></div>
          <div><dt>Estado del trámite</dt><dd>{recibida ? "Recibida por la Delegación" : solicitud.estado === "con_faltantes" ? "Con documentos faltantes" : "En revisión documental"}</dd></div>
        </dl>
        {solicitud.estado === "con_faltantes" && (
          <div className="s2-mensaje error">
            <strong>Documentos por corregir</strong>
            <ul>{solicitud.faltantes.map((item) => <li key={item.clave}>{item.nombre}{item.observacion ? `: ${item.observacion}` : ""}</li>)}</ul>
            {solicitud.observacion_recepcion && <p>{solicitud.observacion_recepcion}</p>}
            <p>La notificación por correo y el plazo para atender observaciones corresponden a HU-08.</p>
          </div>
        )}
        <div className="acciones">
          {solicitud.acuse_disponible
            ? <a className="s2-boton primario" href={`/api/solicitudes/${id}/acuse`}>Descargar acuse (PDF)</a>
            : <button className="s2-boton primario" disabled>Descargar acuse (PDF)</button>}
          <Link className="s2-boton secundario" href={`/solicitudes/${id}/paso/1`}>Ver mi solicitud</Link>
        </div>
      </article>
    </div>
  );
}

export default function ConfirmacionSolicitud() {
  return <ProtegidaPorSesion><Contenido /></ProtegidaPorSesion>;
}
