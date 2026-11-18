"use client";
import { useEffect, useState } from "react";
import { api } from "@/compartido/api";
import type { ProgramaPortal } from "@/compartido/tipos";
import { FiltrosPortal, type ValoresFiltro } from "@/modulos/convocatorias/FiltrosPortal";
import { TarjetaPrograma } from "@/modulos/convocatorias/TarjetaPrograma";

/** HU-02: portal público de consulta de convocatorias. */
export default function PaginaPortal() {
  const [filtros, setFiltros] = useState<ValoresFiltro>({ q: "", estado: "", regionId: "", municipioId: "" });
  const [programas, setProgramas] = useState<ProgramaPortal[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const parametros = new URLSearchParams();
    if (filtros.q.trim()) parametros.set("q", filtros.q.trim());
    if (filtros.estado) parametros.set("estado", filtros.estado);
    const demora = setTimeout(() => {
      api.obtener<ProgramaPortal[]>(`/api/publico/programas?${parametros}`)
        .then((d) => { setProgramas(d); setError(""); })
        .catch((e: Error) => setError(e.message));
    }, 250);
    return () => clearTimeout(demora);
  }, [filtros.q, filtros.estado]);

  return (
    <>
      <h1>Convocatorias de apoyos forestales</h1>
      <p className="nota">Consulta los programas de PROBOSQUE y elige tu región y municipio para conocer la Delegación Regional Forestal que te atiende.</p>
      <FiltrosPortal valores={filtros} alCambiar={setFiltros} />
      {error && <div className="error">{error}</div>}
      {programas === null && !error && <p>Cargando…</p>}
      {programas?.length === 0 && <div className="aviso">No hay programas que coincidan con tu búsqueda.</div>}
      <div className="rejilla">
        {programas?.map((p) => <TarjetaPrograma key={p.clave} programa={p} municipioId={filtros.municipioId} />)}
      </div>
    </>
  );
}
