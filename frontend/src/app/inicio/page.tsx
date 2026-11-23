"use client";
import Link from "next/link";
import { ProtegidaPorSesion } from "@/compartido/ProtegidaPorSesion";
import { useSesion } from "@/modulos/acceso/ContextoSesion";

function Contenido() {
  const { sesion } = useSesion();
  if (!sesion) return null;
  return (
    <>
      <h1>Hola, {sesion.nombre_completo}</h1>
      <p className="nota">Rol: {sesion.rol.nombre}{sesion.region ? ` · ${sesion.region.nombre}` : ""}</p>
      <div className="acciones" style={{ marginTop: "1.5rem" }}>
        {sesion.bloques.map((bloque) => (
          <Link key={bloque.clave} className="tarjeta" href={bloque.ruta}>
            <strong>{bloque.titulo}</strong>
            <span>{bloque.descripcion}</span>
          </Link>
        ))}
      </div>
    </>
  );
}

export default function PaginaInicio() {
  return <ProtegidaPorSesion><Contenido /></ProtegidaPorSesion>;
}
