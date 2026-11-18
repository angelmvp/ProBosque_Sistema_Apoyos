"use client";
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/compartido/api";
import { ETIQUETA_ESTADO, fechaCorta } from "@/compartido/formato";
import type { DetallePrograma } from "@/compartido/tipos";

/** HU-02: detalle de un programa con visor de PDF único, formatos y delegación. */
export default function PaginaPrograma() {
  const { clave } = useParams<{ clave: string }>();
  const municipio = useSearchParams().get("municipio");
  const [d, setD] = useState<DetallePrograma | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.obtener<DetallePrograma>(`/api/publico/programas/${clave}${municipio ? `?municipio_id=${municipio}` : ""}`)
      .then(setD).catch((e: Error) => setError(e.message));
  }, [clave, municipio]);

  if (error) return <div className="error">{error}</div>;
  if (!d) return <p>Cargando…</p>;
  const pub = d.publicacion;

  return (
    <>
      <p><Link href="/">← Volver a convocatorias</Link></p>
      <h1>{d.nombre}</h1>
      <span className={`etiqueta ${d.estado}`}>{ETIQUETA_ESTADO[d.estado]}</span>
      <div className="dos-columnas">
        <section>
          {pub?.url_pdf ? (
            <>
              <h2>{pub.titulo}</h2>
              <p className="nota">Vigencia: {fechaCorta(pub.vigencia_inicio)} al {fechaCorta(pub.vigencia_fin)} · <a href={pub.url_pdf} target="_blank" rel="noreferrer">Abrir PDF en otra pestaña</a></p>
              {d.estado === "historica" && <div className="aviso">Esta convocatoria ya concluyó. Se muestra solo como consulta.</div>}
              <iframe className="visor" src={pub.url_pdf} title={`Convocatoria: ${pub.titulo}`} />
            </>
          ) : (
            <div className="aviso">Por ahora no hay una convocatoria abierta para este programa.</div>
          )}
        </section>
        <aside>
          <div className="tarjeta">
            <h2>Delegación que te atiende</h2>
            {d.delegacion ? (
              <>
                <strong>{d.delegacion.nombre}</strong>
                {d.municipio && <span className="nota">Municipio: {d.municipio.nombre}</span>}
                <span>Domicilio: {d.delegacion.domicilio ?? "por confirmar"}</span>
                <span>Teléfono: {d.delegacion.telefono ?? "por confirmar"}</span>
                <span>Horario: {d.delegacion.horario ?? "por confirmar"}</span>
              </>
            ) : (
              <span className="nota">Elige un municipio en el portal para ver tu delegación.</span>
            )}
          </div>
          <div className="tarjeta" style={{ marginTop: "1rem" }}>
            <h2>Formatos descargables</h2>
            {d.formatos.length ? d.formatos.map((f) => <a key={f.clave} href={f.url}>{f.nombre}</a>) : <span className="nota">Sin formatos asociados.</span>}
          </div>
        </aside>
      </div>
    </>
  );
}
