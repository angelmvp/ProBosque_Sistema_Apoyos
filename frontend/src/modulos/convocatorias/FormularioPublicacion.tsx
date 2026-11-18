"use client";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { api } from "@/compartido/api";
import type { ProgramaPortal, PublicacionAdmin } from "@/compartido/tipos";

/** HU-03: alta y edición (solo borradores) de una publicación con su PDF único. */
export function FormularioPublicacion({ existente }: { existente?: PublicacionAdmin }) {
  const router = useRouter();
  const [programas, setProgramas] = useState<ProgramaPortal[]>([]);
  const [programa, setPrograma] = useState(existente?.programa_clave ?? "");
  const [titulo, setTitulo] = useState(existente?.titulo ?? "");
  const [inicio, setInicio] = useState(existente?.vigencia_inicio ?? "");
  const [fin, setFin] = useState(existente?.vigencia_fin ?? "");
  const [archivo, setArchivo] = useState<File | null>(null);
  const [error, setError] = useState("");
  const [enviando, setEnviando] = useState(false);

  useEffect(() => { api.obtener<ProgramaPortal[]>("/api/publico/programas").then(setProgramas).catch(() => {}); }, []);

  async function enviar(accion: "borrador" | "publicar") {
    setError("");
    if (accion === "publicar" && !archivo && !existente?.nombre_archivo) {
      setError("Para publicar necesitas adjuntar el PDF de la convocatoria."); return;
    }
    if (accion === "publicar" && !window.confirm("Una vez publicada, la convocatoria no se puede modificar ni despublicar. ¿Publicar?")) return;
    const datos = new FormData();
    datos.set("programa", programa); datos.set("titulo", titulo);
    datos.set("vigencia_inicio", inicio); datos.set("vigencia_fin", fin); datos.set("accion", accion);
    if (archivo) datos.set("archivo", archivo);
    setEnviando(true);
    try {
      await api.enviarFormulario<PublicacionAdmin>(existente ? `/api/publicaciones/${existente.id}` : "/api/publicaciones", datos, existente ? "PUT" : "POST");
      router.push("/admin/publicaciones");
    } catch (e) { setError((e as Error).message); } finally { setEnviando(false); }
  }

  return (
    <form className="formulario" onSubmit={(e: FormEvent) => { e.preventDefault(); void enviar("borrador"); }}>
      {error && <div className="error" role="alert">{error}</div>}
      <label className="campo">Programa
        <select required value={programa} onChange={(e) => setPrograma(e.target.value)}>
          <option value="">Selecciona…</option>
          {programas.map((p) => <option key={p.clave} value={p.clave}>{p.nombre}</option>)}
        </select>
      </label>
      <label className="campo">Título<input required maxLength={200} value={titulo} onChange={(e) => setTitulo(e.target.value)} /></label>
      <label className="campo">Vigencia: inicio<input type="date" required value={inicio} onChange={(e) => setInicio(e.target.value)} /></label>
      <label className="campo">Vigencia: fin<input type="date" required value={fin} onChange={(e) => setFin(e.target.value)} /></label>
      <label className="campo">PDF de la convocatoria (reglas, requisitos y formatos en un solo archivo)
        <input type="file" accept="application/pdf" onChange={(e) => setArchivo(e.target.files?.[0] ?? null)} />
        {existente?.nombre_archivo && !archivo && <span className="nota">Archivo actual: {existente.nombre_archivo}</span>}
      </label>
      <div className="acciones">
        <button className="boton secundario" disabled={enviando}>Guardar borrador</button>
        <button type="button" className="boton" disabled={enviando} onClick={() => void enviar("publicar")}>Publicar</button>
      </div>
    </form>
  );
}
