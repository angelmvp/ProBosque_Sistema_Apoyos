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
    <>
      <div className="encabezado-pagina">
        <div><p className="eyebrow">SOLICITUDES DE APOYO</p><h1>Mis solicitudes</h1></div>
        <Link className="boton" href="/solicitudes/nueva">Nueva solicitud</Link>
      </div>
      {error && <p className="alerta">{error}</p>}
      {!solicitudes.length && !error && <p className="nota">Aún no tienes solicitudes. Inicia una nueva para comenzar.</p>}
      <div className="lista-tarjetas">
        {solicitudes.map((solicitud) => (
          <Link className="tarjeta" href={`/solicitudes/${solicitud.id}`} key={solicitud.id}>
            <strong>{solicitud.programa}</strong>
            <span>{solicitud.municipio} · {solicitud.estado}</span>
            {solicitud.folio && <span>Folio: {solicitud.folio}</span>}
            {solicitud.faltantes.length > 0 && <span className="alerta">Faltan {solicitud.faltantes.length} requisitos</span>}
          </Link>
        ))}
      </div>
    </>
  );
}

export default function PaginaSolicitudes() {
  return <ProtegidaPorSesion><Contenido /></ProtegidaPorSesion>;
}
