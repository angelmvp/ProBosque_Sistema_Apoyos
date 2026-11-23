"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useSesion } from "@/modulos/acceso/ContextoSesion";

export function Encabezado() {
  const { sesion, cargando, salir } = useSesion();
  const router = useRouter();
  return (
    <header className="encabezado">
      <Link href="/" className="marca">PROBOSQUE <span>Apoyos forestales</span></Link>
      <nav>
        <Link href="/">Convocatorias</Link>
        {sesion?.menu.filter((o) => o.clave !== "inicio").map((o) => (
          <Link key={o.clave} href={o.ruta}>{o.etiqueta}</Link>
        ))}
        {sesion && <Link href="/inicio">Mi inicio</Link>}
      </nav>
      <div className="sesion">
        {cargando ? null : sesion ? (
          <>
            <Link href="/perfil" title={sesion.correo}>
              {sesion.nombre_completo} · <em>{sesion.rol.nombre}</em>
            </Link>
            <button className="boton secundario" onClick={async () => { await salir(); router.push("/"); }}>Salir</button>
          </>
        ) : (
          <Link className="boton" href="/ingresar">Ingresar</Link>
        )}
      </div>
    </header>
  );
}
