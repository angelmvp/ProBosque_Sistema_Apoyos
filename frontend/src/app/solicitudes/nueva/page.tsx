"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { api } from "@/compartido/api";
import { ProtegidaPorSesion } from "@/compartido/ProtegidaPorSesion";

type Opcion = { id: number; nombre: string };

function Contenido() {
  const [programas, setProgramas] = useState<Opcion[]>([]);
  const [municipios, setMunicipios] = useState<Opcion[]>([]);
  const [programa, setPrograma] = useState("");
  const [municipio, setMunicipio] = useState("");
  const [mensaje, setMensaje] = useState("");
  useEffect(() => {
    api.obtener<Opcion[]>("/api/solicitudes/catalogos/programas").then(setProgramas).catch((e) => setMensaje(e.message));
    api.obtener<Opcion[]>("/api/solicitudes/catalogos/municipios").then(setMunicipios).catch((e) => setMensaje(e.message));
  }, []);
  async function crear(evento: FormEvent) {
    evento.preventDefault();
    try {
      const solicitud = await api.enviarJson<{ id: number }>("/api/solicitudes", {
        programa_id: Number(programa), municipio_id: Number(municipio),
      });
      setMensaje(`Solicitud ${solicitud.id} creada. Ya puedes completar sus formularios y documentos.`);
    } catch (e) { setMensaje((e as Error).message); }
  }
  return (
    <>
      <p className="eyebrow">NUEVA SOLICITUD</p><h1>Iniciar solicitud de apoyo</h1>
      <p className="nota">Primero selecciona el programa y el municipio del predio.</p>
      <form className="formulario" onSubmit={crear}>
        <label>Programa<select required value={programa} onChange={(e) => setPrograma(e.target.value)}>
          <option value="">Selecciona un programa</option>{programas.map((item) => <option key={item.id} value={item.id}>{item.nombre}</option>)}
        </select></label>
        <label>Municipio<select required value={municipio} onChange={(e) => setMunicipio(e.target.value)}>
          <option value="">Selecciona un municipio</option>{municipios.map((item) => <option key={item.id} value={item.id}>{item.nombre}</option>)}
        </select></label>
        <button className="boton" type="submit">Crear borrador</button>
      </form>
      {mensaje && <p className="nota">{mensaje}</p>}
      <Link href="/solicitudes">Volver a mis solicitudes</Link>
    </>
  );
}

export default function NuevaSolicitud() {
  return <ProtegidaPorSesion><Contenido /></ProtegidaPorSesion>;
}
