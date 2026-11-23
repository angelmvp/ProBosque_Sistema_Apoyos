"use client";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { api } from "@/compartido/api";
import type { ProgramaPortal, PublicacionAdmin } from "@/compartido/tipos";

/** HU-03: alta y edición (solo borradores) de una publicación con múltiples archivos. */
export function FormularioPublicacion({ existente }: { existente?: PublicacionAdmin }) {
  const router = useRouter();
  const [programas, setProgramas] = useState<ProgramaPortal[]>([]);
  const [programa, setPrograma] = useState(existente?.programa_clave ?? "");
  const [titulo, setTitulo] = useState(existente?.titulo ?? "");
  const [inicio, setInicio] = useState(existente?.vigencia_inicio ?? "");
  const [fin, setFin] = useState(existente?.vigencia_fin ?? "");
  const [archivos, setArchivos] = useState<Array<{ archivo: File; tipo: string; etiqueta: string }>>([]);
  const [error, setError] = useState("");
  const [enviando, setEnviando] = useState(false);

  useEffect(() => { api.obtener<ProgramaPortal[]>("/api/publico/programas").then(setProgramas).catch(() => {}); }, []);

  async function enviar(accion: "borrador" | "publicar") {
    setError("");
    const tieneConvocatoriaNueva = archivos.some((item) => item.tipo === "convocatoria");
    const tieneConvocatoriaExistente = existente?.archivos.some((item) => item.tipo === "convocatoria");
    if (accion === "publicar" && !tieneConvocatoriaNueva && !tieneConvocatoriaExistente) {
      setError("Para publicar necesitas adjuntar al menos un archivo de tipo convocatoria."); return;
    }
    if (archivos.some((item) => item.tipo === "otro" && !item.etiqueta.trim())) {
      setError("La etiqueta es obligatoria para archivos de tipo otro."); return;
    }
    if (accion === "publicar" && !window.confirm("Una vez publicada, la convocatoria no se puede modificar ni despublicar. ¿Publicar?")) return;
    const datos = new FormData();
    datos.set("programa", programa); datos.set("titulo", titulo);
    datos.set("vigencia_inicio", inicio); datos.set("vigencia_fin", fin); datos.set("accion", accion);
    archivos.forEach((item, indice) => {
      datos.append("archivos", item.archivo);
      datos.append("tipos", item.tipo);
      datos.append("etiquetas", item.etiqueta.trim() || item.tipo);
    });
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
      {existente?.archivos.length ? (
        <fieldset>
          <legend>Archivos actuales</legend>
          {existente.archivos.map((item) => (
            <div className="fila" key={item.id}>
              <span>{item.nombre_original}</span>
              <select
                value={item.tipo}
                onChange={async (e) => {
                  const datos = new FormData();
                  datos.set("tipo", e.target.value);
                  datos.set("etiqueta", item.etiqueta);
                  await api.enviarFormulario(`/api/publicaciones/${existente.id}/archivos/${item.id}`, datos, "PATCH");
                  window.location.reload();
                }}
              >
                <option value="convocatoria">Convocatoria</option>
                <option value="reglas_operacion">Reglas de operación</option>
                <option value="formato">Formato</option>
                <option value="anexo">Anexo</option>
                <option value="otro">Otro</option>
              </select>
              <input
                defaultValue={item.etiqueta}
                onBlur={async (e) => {
                  const datos = new FormData();
                  datos.set("tipo", item.tipo);
                  datos.set("etiqueta", e.target.value);
                  await api.enviarFormulario(`/api/publicaciones/${existente.id}/archivos/${item.id}`, datos, "PATCH");
                  window.location.reload();
                }}
              />
              <button
                type="button"
                className="boton peligro"
                onClick={async () => {
                  await api.accion(`/api/publicaciones/${existente.id}/archivos/${item.id}`, "DELETE");
                  window.location.reload();
                }}
              >Quitar</button>
            </div>
          ))}
        </fieldset>
      ) : null}
      <fieldset>
        <legend>Agregar archivos</legend>
        <label className="campo">Seleccionar uno o varios archivos
          <input
            type="file"
            accept=".pdf,.docx,.xlsx,application/pdf"
            multiple
            onChange={(e) => {
              const seleccionados = Array.from(e.target.files ?? []);
              setArchivos(seleccionados.map((archivo) => ({
                archivo,
                tipo: "convocatoria",
                etiqueta: "Convocatoria",
              })));
            }}
          />
        </label>
        {archivos.map((item, indice) => (
          <div className="fila" key={`${item.archivo.name}-${indice}`}>
            <span>{item.archivo.name}</span>
            <select value={item.tipo} onChange={(e) => setArchivos((actual) => actual.map((v, i) =>
              i === indice ? { ...v, tipo: e.target.value, etiqueta: e.target.value === "otro" ? "" : {
                convocatoria: "Convocatoria",
                reglas_operacion: "Reglas de operación",
                formato: "Formato",
                anexo: "Anexo",
              }[e.target.value] ?? "Otro" } : v))}>
              <option value="convocatoria">Convocatoria</option>
              <option value="reglas_operacion">Reglas de operación</option>
              <option value="formato">Formato</option>
              <option value="anexo">Anexo</option>
              <option value="otro">Otro</option>
            </select>
            <input
              value={item.etiqueta}
              placeholder="Etiqueta visible"
              onChange={(e) => setArchivos((actual) => actual.map((v, i) =>
                i === indice ? { ...v, etiqueta: e.target.value } : v))}
            />
          </div>
        ))}
      </fieldset>
      <div className="acciones">
        <button className="boton secundario" disabled={enviando}>Guardar borrador</button>
        <button type="button" className="boton" disabled={enviando} onClick={() => void enviar("publicar")}>Publicar</button>
      </div>
    </form>
  );
}
