"use client";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/compartido/api";
import { ProtegidaPorSesion } from "@/compartido/ProtegidaPorSesion";
import type { PublicacionAdmin } from "@/compartido/tipos";
import { FormularioPublicacion } from "@/modulos/convocatorias/FormularioPublicacion";

function Contenido() {
  const { id } = useParams<{ id: string }>();
  const [p, setP] = useState<PublicacionAdmin | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { api.obtener<PublicacionAdmin>(`/api/publicaciones/${id}`).then(setP).catch((e: Error) => setError(e.message)); }, [id]);
  if (error) return <div className="error">{error}</div>;
  if (!p) return <p>Cargando…</p>;
  if (p.estado !== "borrador") return <div className="aviso">Esta publicación ya fue publicada y no se puede modificar.</div>;
  return <><h1>Editar borrador</h1><FormularioPublicacion existente={p} /></>;
}

export default function PaginaEditarPublicacion() {
  return <ProtegidaPorSesion permiso="publicaciones.gestionar"><Contenido /></ProtegidaPorSesion>;
}
