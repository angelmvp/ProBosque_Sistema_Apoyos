"use client";
import type { ArchivoPublicacion } from "@/compartido/tipos";

export function ListaArchivosPublicacion({ archivos }: { archivos: ArchivoPublicacion[] }) {
  if (!archivos.length) return <span className="nota">Sin documentos adjuntos.</span>;
  return (
    <div className="documentos">
      {archivos.map((archivo) => (
        <div className="documento" key={archivo.id}>
          <strong>{archivo.etiqueta}</strong>
          <a href={archivo.url} target="_blank" rel="noreferrer">{archivo.nombre_original}</a>
        </div>
      ))}
    </div>
  );
}
