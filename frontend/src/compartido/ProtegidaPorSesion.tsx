"use client";
import Link from "next/link";
import type { ReactNode } from "react";
import { useSesion } from "@/modulos/acceso/ContextoSesion";

/** Muestra el contenido solo con sesión (y permiso, si se indica); si no, la pantalla de acceso denegado. */
export function ProtegidaPorSesion({ permiso, permisos, children }: {
  permiso?: string; permisos?: string[]; children: ReactNode
}) {
  const { sesion, cargando, tiene } = useSesion();
  if (cargando) return <p>Cargando…</p>;
  if (!sesion) return <div className="aviso">Necesitas iniciar sesión. <Link href="/ingresar">Ingresar</Link></div>;
  const permitido = permiso ? tiene(permiso) : !permisos || permisos.some((valor) => tiene(valor));
  if (!permitido) return <PantallaAccesoDenegado />;
  return <>{children}</>;
}

export function PantallaAccesoDenegado() {
  return (
    <div className="error" role="alert">
      <h1>Acceso denegado</h1>
      <p>Tu rol no tiene permiso para ver esta sección. El intento quedó registrado.</p>
      <Link href="/inicio">Volver a mi inicio</Link>
    </div>
  );
}
