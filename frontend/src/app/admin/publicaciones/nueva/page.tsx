"use client";
import { ProtegidaPorSesion } from "@/compartido/ProtegidaPorSesion";
import { FormularioPublicacion } from "@/modulos/convocatorias/FormularioPublicacion";

export default function PaginaNuevaPublicacion() {
  return (
    <ProtegidaPorSesion permiso="publicaciones.gestionar">
      <h1>Nueva publicación</h1>
      <FormularioPublicacion />
    </ProtegidaPorSesion>
  );
}
