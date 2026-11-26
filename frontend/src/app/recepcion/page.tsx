"use client";

import { useEffect, useState } from "react";
import { api } from "@/compartido/api";
import { ProtegidaPorSesion } from "@/compartido/ProtegidaPorSesion";

type Recepcion = { id: number; programa: string; municipio: string; estado: string; folio: string | null; faltantes: { nombre: string }[] };

function Contenido() {
  const [items, setItems] = useState<Recepcion[]>([]);
  const [mensaje, setMensaje] = useState("");
  const cargar = () => api.obtener<Recepcion[]>("/api/recepcion/solicitudes").then(setItems).catch((e) => setMensaje(e.message));
  useEffect(() => { cargar(); }, []);
  async function recibir(id: number) {
    try { await api.enviarJson(`/api/recepcion/solicitudes/${id}/recibir`, {}); setMensaje("Solicitud procesada."); cargar(); }
    catch (e) { setMensaje((e as Error).message); }
  }
  return <div className="sprint2-page recepcion-page">
    <p className="eyebrow">DELEGACIÓN REGIONAL</p>
    <h1>Recepción de solicitudes</h1>
    {mensaje && <p className="nota">{mensaje}</p>}
    <div className="lista-tarjetas">{items.map((item) => <article className="tarjeta recepcion-tarjeta" key={item.id}>
      <strong>{item.programa}</strong>
      <span>{item.municipio} · {item.estado}</span>
      {item.faltantes.length ? (
        <span className="sprint2-estado pendiente">Requisitos faltantes: {item.faltantes.length}</span>
      ) : (
        <>
          <span className="sprint2-estado">Documentación completa</span>
          <button className="boton" onClick={() => recibir(item.id)}>Recibir y generar folio</button>
        </>
      )}
    </article>)}</div>
  </div>;
}

export default function RecepcionPage() {
  return <ProtegidaPorSesion><Contenido /></ProtegidaPorSesion>;
}
