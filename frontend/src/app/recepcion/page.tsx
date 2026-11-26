"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";
import { api } from "@/compartido/api";
import { ProtegidaPorSesion } from "@/compartido/ProtegidaPorSesion";

type Recepcion = {
  id: number; programa: string; programa_clave: string; municipio: string;
  estado: string; folio: string | null; nombre_solicitante: string;
  enviada_en: string | null;
};

function Contenido() {
  const [items, setItems] = useState<Recepcion[]>([]);
  const [programa, setPrograma] = useState("");
  const [estado, setEstado] = useState("");
  const [municipio, setMunicipio] = useState("");
  const [fechaDesde, setFechaDesde] = useState("");
  const [fechaHasta, setFechaHasta] = useState("");
  const [mensaje, setMensaje] = useState("");

  const cargar = (evento?: FormEvent) => {
    evento?.preventDefault();
    const parametros = new URLSearchParams();
    if (programa) parametros.set("programa", programa);
    if (estado) parametros.set("estado", estado);
    if (municipio) parametros.set("municipio", municipio);
    if (fechaDesde) parametros.set("fecha_desde", fechaDesde);
    if (fechaHasta) parametros.set("fecha_hasta", fechaHasta);
    api.obtener<Recepcion[]>(`/api/recepcion/solicitudes?${parametros}`)
      .then(setItems).catch((e) => setMensaje(e.message));
  };
  useEffect(() => { cargar(); }, []);

  return <div className="sprint2-page recepcion-page">
    <p className="eyebrow">DELEGACIÓN REGIONAL FORESTAL · MK-07-1</p>
    <h1>Solicitudes por recibir</h1>
    <p className="nota">La bandeja muestra las solicitudes de tu región.</p>
    {mensaje && <p className="s2-mensaje" role="status">{mensaje}</p>}
    <form className="s2-filtros-recepcion" onSubmit={(evento) => cargar(evento)}>
      <label className="s2-campo"><span>Programa</span>
        <select value={programa} onChange={(evento) => setPrograma(evento.target.value)}>
          <option value="">Todos</option>
          <option value="capturando_carbono">Capturando Carbono</option>
          <option value="plantaciones_sustentables">Plantaciones Sustentables</option>
          <option value="restauracion_hidrologico_forestal">Restauración Hidrológico-Forestal</option>
        </select>
      </label>
      <label className="s2-campo"><span>Estado</span>
        <select value={estado} onChange={(evento) => setEstado(evento.target.value)}>
          <option value="">Todos</option>
          <option value="enviada">Enviada</option>
          <option value="con_faltantes">Con faltantes</option>
          <option value="recibida">Recibida</option>
        </select>
      </label>
      <label className="s2-campo"><span>Municipio</span>
        <input value={municipio} onChange={(evento) => setMunicipio(evento.target.value)} />
      </label>
      <label className="s2-campo"><span>Enviada desde</span>
        <input type="date" value={fechaDesde} onChange={(evento) => setFechaDesde(evento.target.value)} />
      </label>
      <label className="s2-campo"><span>Enviada hasta</span>
        <input type="date" value={fechaHasta} onChange={(evento) => setFechaHasta(evento.target.value)} />
      </label>
      <button className="s2-boton primario" type="submit">Filtrar</button>
    </form>
    {!items.length ? <p className="s2-vacio">No hay solicitudes para los filtros seleccionados.</p> :
      <div className="s2-tabla-contenedor">
        <table className="s2-tabla">
          <thead><tr><th>Programa</th><th>Persona solicitante</th><th>Municipio</th>
            <th>Fecha de envío</th><th>Estado</th><th>Acción</th></tr></thead>
          <tbody>{items.map((item) => (
            <tr key={item.id}>
              <td>{item.programa}</td><td>{item.nombre_solicitante}</td><td>{item.municipio}</td>
              <td>{item.enviada_en ? new Date(item.enviada_en).toLocaleString("es-MX") : "—"}</td>
              <td><span className={`s2-etiqueta ${item.estado === "recibida" ? "s2-exito" : item.estado === "con_faltantes" ? "s2-error" : "s2-aviso"}`}>{item.estado.replace("_", " ")}</span></td>
              <td><Link className="s2-enlace" href={`/recepcion/${item.id}`}>Revisar</Link></td>
            </tr>
          ))}</tbody>
        </table>
      </div>}
  </div>;
}

export default function RecepcionPage() {
  return <ProtegidaPorSesion><Contenido /></ProtegidaPorSesion>;
}
