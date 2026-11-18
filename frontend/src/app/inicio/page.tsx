"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { api, ErrorApi } from "@/compartido/api";
import { ProtegidaPorSesion } from "@/compartido/ProtegidaPorSesion";
import { useSesion } from "@/modulos/acceso/ContextoSesion";

interface Expediente { folio: string; programa: string; delegacion: string; tramite: string }

function Contenido() {
  const { sesion, tiene } = useSesion();
  const [expedientes, setExpedientes] = useState<Expediente[] | null>(null);
  const [error, setError] = useState("");
  const puedeVer = tiene("expedientes.ver_todos") || tiene("expedientes.ver_delegacion");

  useEffect(() => {
    if (!puedeVer) return;
    api.obtener<Expediente[]>("/api/expedientes").then(setExpedientes)
      .catch((e) => setError(e instanceof ErrorApi ? e.message : "Error al cargar."));
  }, [puedeVer]);

  if (!sesion) return null;
  return (
    <>
      <h1>Hola, {sesion.nombre}</h1>
      <p className="nota">Rol: {sesion.rol.nombre}{sesion.region ? ` · ${sesion.region.nombre}` : ""}</p>
      <h2>Tus opciones</h2>
      <div className="acciones">
        {sesion.menu.map((o) => <Link key={o.clave} className="boton secundario" href={o.ruta}>{o.etiqueta}</Link>)}
      </div>
      {puedeVer && (
        <>
          <h2>Expedientes visibles para tu rol</h2>
          <p className="nota">Datos ficticios de demostración.</p>
          {error && <div className="error">{error}</div>}
          {expedientes?.length === 0 && <div className="aviso">No hay expedientes para mostrar.</div>}
          {!!expedientes?.length && (
            <table><thead><tr><th>Folio</th><th>Programa</th><th>Delegación</th><th>Trámite</th></tr></thead>
              <tbody>{expedientes.map((e) => <tr key={e.folio}><td>{e.folio}</td><td>{e.programa}</td><td>{e.delegacion}</td><td>{e.tramite}</td></tr>)}</tbody></table>
          )}
        </>
      )}
      <p className="nota" style={{ marginTop: "2rem" }}>Prueba de acceso denegado (HU-01): abre <Link href="/dictamenes">Dictámenes</Link>; solo la Dirección de Restauración y Fomento Forestal tiene permiso.</p>
    </>
  );
}

export default function PaginaInicio() {
  return <ProtegidaPorSesion><Contenido /></ProtegidaPorSesion>;
}
