"use client";
import { useEffect, useState } from "react";
import { api } from "@/compartido/api";
import type { Municipio, Region } from "@/compartido/tipos";

export interface ValoresFiltro { q: string; estado: string; regionId: string; municipioId: string }

/** Filtros del portal (HU-02): nombre del programa, estado, región y municipio. */
export function FiltrosPortal({ valores, alCambiar }: { valores: ValoresFiltro; alCambiar: (v: ValoresFiltro) => void }) {
  const [regiones, setRegiones] = useState<Region[]>([]);
  const [municipios, setMunicipios] = useState<Municipio[]>([]);

  useEffect(() => { api.obtener<Region[]>("/api/publico/regiones").then(setRegiones).catch(() => setRegiones([])); }, []);
  useEffect(() => {
    const ruta = valores.regionId ? `/api/publico/municipios?region_id=${valores.regionId}` : "/api/publico/municipios";
    api.obtener<Municipio[]>(ruta).then(setMunicipios).catch(() => setMunicipios([]));
  }, [valores.regionId]);

  return (
    <div className="filtros" role="search">
      <label className="campo">Programa
        <input value={valores.q} placeholder="Buscar por nombre" onChange={(e) => alCambiar({ ...valores, q: e.target.value })} />
      </label>
      <label className="campo">Estado
        <select value={valores.estado} onChange={(e) => alCambiar({ ...valores, estado: e.target.value })}>
          <option value="">Todos</option>
          <option value="vigente">Convocatoria abierta</option>
          <option value="historica">Concluida</option>
          <option value="sin_convocatoria">Sin convocatoria</option>
        </select>
      </label>
      <label className="campo">Región (Delegación Regional Forestal)
        <select value={valores.regionId} onChange={(e) => alCambiar({ ...valores, regionId: e.target.value, municipioId: "" })}>
          <option value="">Todas</option>
          {regiones.map((r) => <option key={r.id} value={r.id}>{r.nombre}</option>)}
        </select>
      </label>
      <label className="campo">Municipio
        <select value={valores.municipioId} onChange={(e) => alCambiar({ ...valores, municipioId: e.target.value })}>
          <option value="">Todos</option>
          {municipios.map((m) => <option key={m.id} value={m.id}>{m.nombre}</option>)}
        </select>
      </label>
    </div>
  );
}
