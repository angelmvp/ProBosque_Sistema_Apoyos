"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { useRouter } from "next/navigation";
import { api } from "@/compartido/api";
import type { RequisitoSolicitud, Solicitud } from "@/compartido/tipos";
import { ProtegidaPorSesion } from "@/compartido/ProtegidaPorSesion";

function Contenido() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [solicitud, setSolicitud] = useState<Solicitud | null>(null);
  const [requisitos, setRequisitos] = useState<RequisitoSolicitud[]>([]);
  const [datos, setDatos] = useState({ curp: "", codigo_postal: "", telefono_celular: "" });
  const [archivo, setArchivo] = useState<File | null>(null);
  const [requisito, setRequisito] = useState("identificacion");
  const [mensaje, setMensaje] = useState("");
  const cargar = () => {
    api.obtener<Solicitud>(`/api/solicitudes/${id}`).then(setSolicitud).catch((e) => setMensaje(e.message));
    api.obtener<RequisitoSolicitud[]>(`/api/solicitudes/${id}/requisitos`).then(setRequisitos).catch((e) => setMensaje(e.message));
  };
  useEffect(() => { cargar(); }, [id]);
  useEffect(() => {
    if (!solicitud) return;
    router.replace(solicitud.estado === "borrador"
      ? `/solicitudes/${id}/paso/1` : `/solicitudes/${id}/confirmacion`);
  }, [id, router, solicitud]);
  async function guardar(evento: FormEvent) {
    evento.preventDefault();
    try { await api.enviarJson(`/api/solicitudes/${id}`, { datos_502: datos, aviso_privacidad: true }, "PUT"); setMensaje("Datos guardados."); cargar(); }
    catch (e) { setMensaje((e as Error).message); }
  }
  async function subir(evento: FormEvent) {
    evento.preventDefault();
    if (!archivo) return;
    const form = new FormData(); form.append("requisito", requisito); form.append("archivo", archivo);
    try { await api.enviarFormulario(`/api/solicitudes/${id}/documentos`, form); setMensaje("Documento agregado."); setArchivo(null); cargar(); }
    catch (e) { setMensaje((e as Error).message); }
  }
  async function enviar() {
    try { await api.accion(`/api/solicitudes/${id}/enviar`); setMensaje("Solicitud enviada a tu delegación."); cargar(); }
    catch (e) { setMensaje((e as Error).message); }
  }
  if (!solicitud) return <div className="sprint2-page solicitud-detalle-page"><p>{mensaje || "Cargando solicitud..."}</p></div>;
  const editable = solicitud.estado === "borrador";
  return (
    <div className="sprint2-page solicitud-detalle-page">
      <Link href="/solicitudes">← Mis solicitudes</Link>
      <div className="solicitud-detalle-cabecera">
        <p className="eyebrow">SOLICITUD {solicitud.id}</p>
        <h1>{solicitud.programa}</h1>
        <p className="nota">{solicitud.municipio} · {solicitud.estado}</p>
        {solicitud.folio && <p className="nota">Folio asignado: <strong>{solicitud.folio}</strong></p>}
      </div>
      {mensaje && <p className="nota">{mensaje}</p>}
      {editable && <form className="formulario solicitud-detalle-formulario" onSubmit={guardar}>
        <h2>Registro de información (502)</h2>
        <label>CURP<input value={datos.curp} onChange={(e) => setDatos({ ...datos, curp: e.target.value })} maxLength={18} /></label>
        <label>Código postal<input value={datos.codigo_postal} onChange={(e) => setDatos({ ...datos, codigo_postal: e.target.value })} maxLength={5} /></label>
        <label>Teléfono celular<input value={datos.telefono_celular} onChange={(e) => setDatos({ ...datos, telefono_celular: e.target.value })} maxLength={10} /></label>
        <button className="boton" type="submit">Guardar datos</button>
      </form>}
      <section className="tarjeta solicitud-documentos">
        <h2>Documentos</h2>
        <ul>{requisitos.map((item) => (
          <li key={item.clave}>
            <span>{item.nombre}</span>
            <span className={`sprint2-estado${item.entregado ? "" : " pendiente"}`}>{item.entregado ? "Entregado" : "Pendiente"}</span>
          </li>
        ))}</ul>
      </section>
      {editable && <form className="formulario solicitud-subir-documento" onSubmit={subir}>
        <label>Requisito<select value={requisito} onChange={(e) => setRequisito(e.target.value)}>{requisitos.map((item) => <option key={item.clave} value={item.clave}>{item.nombre}</option>)}</select></label>
        <label>Archivo<input type="file" accept=".pdf,.jpg,.jpeg,.png" onChange={(e) => setArchivo(e.target.files?.[0] ?? null)} /></label>
        <button className="boton" type="submit">Agregar documento</button>
      </form>}
      {editable && <button className="boton" onClick={enviar}>Enviar solicitud</button>}
    </div>
  );
}

export default function DetalleSolicitud() { return <ProtegidaPorSesion><Contenido /></ProtegidaPorSesion>; }
