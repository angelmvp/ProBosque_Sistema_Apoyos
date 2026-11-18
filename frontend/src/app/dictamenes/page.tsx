"use client";
import { useEffect, useState } from "react";
import { api, ErrorApi } from "@/compartido/api";
import { PantallaAccesoDenegado, ProtegidaPorSesion } from "@/compartido/ProtegidaPorSesion";

/** Marcador de HU-01-CA-2: la sección existe pero solo ciertos roles entran. El backend es quien decide. */
function Contenido() {
  const [estado, setEstado] = useState<"cargando" | "ok" | "denegado">("cargando");
  useEffect(() => {
    api.obtener("/api/dictamenes").then(() => setEstado("ok"))
      .catch((e) => setEstado(e instanceof ErrorApi && e.estado === 403 ? "denegado" : "ok"));
  }, []);
  if (estado === "cargando") return <p>Cargando…</p>;
  if (estado === "denegado") return <PantallaAccesoDenegado />;
  return <><h1>Dictámenes</h1><div className="aviso">Módulo previsto para un sprint posterior. Por ahora solo comprueba el acceso por rol.</div></>;
}

export default function PaginaDictamenes() {
  return <ProtegidaPorSesion><Contenido /></ProtegidaPorSesion>;
}
