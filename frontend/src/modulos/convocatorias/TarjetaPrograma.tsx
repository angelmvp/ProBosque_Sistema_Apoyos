import Link from "next/link";
import { ETIQUETA_ESTADO, fechaCorta } from "@/compartido/formato";
import type { ProgramaPortal } from "@/compartido/tipos";

export function TarjetaPrograma({ programa, municipioId }: { programa: ProgramaPortal; municipioId: string }) {
  const p = programa.publicacion;
  const destino = `/programas/${programa.clave}${municipioId ? `?municipio=${municipioId}` : ""}`;
  return (
    <article className="tarjeta">
      <span className={`etiqueta ${programa.estado}`}>{ETIQUETA_ESTADO[programa.estado]}</span>
      <h2>{programa.nombre}</h2>
      {p ? (
        <p className="nota">{p.titulo}<br />Vigencia: {fechaCorta(p.vigencia_inicio)} al {fechaCorta(p.vigencia_fin)}</p>
      ) : (
        <p className="nota">Por ahora no hay una convocatoria abierta para este programa.</p>
      )}
      <Link className="boton" href={destino}>{programa.convocatoria_abierta ? "Ver convocatoria" : "Ver detalle"}</Link>
    </article>
  );
}
