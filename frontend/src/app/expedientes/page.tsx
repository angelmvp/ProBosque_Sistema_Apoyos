"use client";
import { useEffect, useState } from "react";
import { api, ErrorApi } from "@/compartido/api";
import { ProtegidaPorSesion } from "@/compartido/ProtegidaPorSesion";
import { useSesion } from "@/modulos/acceso/ContextoSesion";

interface Expediente { folio: string; programa: string; delegacion: string; tramite: string }

function Contenido() {
  const { tiene } = useSesion();
  const [expedientes, setExpedientes] = useState<Expediente[] | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    api.obtener<Expediente[]>("/api/expedientes").then(setExpedientes)
      .catch((e) => setError(e instanceof ErrorApi ? e.message : "Error al cargar."));
  }, []);
  return (
    <>
      <h1>{tiene("expedientes.ver_todos") ? "Todos los expedientes" : "Expedientes de mi delegación"}</h1>
      <p className="nota">Datos ficticios de demostración.</p>
      {error && <div className="error">{error}</div>}
      {expedientes?.length === 0 && <div className="aviso">No hay expedientes para mostrar.</div>}
      {!!expedientes?.length && (
        <table><thead><tr><th>Folio</th><th>Programa</th><th>Delegación</th><th>Trámite</th></tr></thead>
          <tbody>{expedientes.map((e) => <tr key={e.folio}><td>{e.folio}</td><td>{e.programa}</td><td>{e.delegacion}</td><td>{e.tramite}</td></tr>)}</tbody></table>
      )}
    </>
  );
}

export default function PaginaExpedientes() {
  return (
    <ProtegidaPorSesion permisos={["expedientes.ver_todos", "expedientes.ver_delegacion"]}>
      <Contenido />
    </ProtegidaPorSesion>
  );
}
