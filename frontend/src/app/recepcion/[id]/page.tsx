"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { api } from "@/compartido/api";
import type { RequisitoSolicitud } from "@/compartido/tipos";
import { ProtegidaPorSesion } from "@/compartido/ProtegidaPorSesion";

type RecepcionDetalle = {
  id: number; programa: string; municipio: string; delegacion: string;
  estado: string; folio: string | null; enviada_en: string | null;
  nombre_solicitante: string; correo_solicitante: string;
  datos_501: Record<string, unknown>; datos_502: Record<string, unknown>;
  documentos: RequisitoSolicitud[];
  faltantes: RequisitoSolicitud[]; acuse_disponible: boolean;
  revision: {
    observacion: string; solicitud_completa: boolean;
    documentos_legibles: boolean; corresponden_al_programa: boolean;
  };
};
type Incidencia = { marcada: boolean; observacion: string };

function mostrar(valor: unknown): string {
  if (valor === null || valor === undefined || valor === "") return "—";
  if (typeof valor === "boolean") return valor ? "Sí" : "No";
  if (Array.isArray(valor)) return valor.join(", ");
  if (typeof valor === "object") {
    return Object.entries(valor as Record<string, unknown>)
      .map(([clave, item]) => `${clave.replaceAll("_", " ")}: ${mostrar(item)}`).join(" · ");
  }
  return String(valor);
}

function Contenido() {
  const { id } = useParams<{ id: string }>();
  const [solicitud, setSolicitud] = useState<RecepcionDetalle | null>(null);
  const [checks, setChecks] = useState({ solicitud_completa: false, documentos_legibles: false, corresponden_al_programa: false });
  const [incidencias, setIncidencias] = useState<Record<string, Incidencia>>({});
  const [observacion, setObservacion] = useState("");
  const [mensaje, setMensaje] = useState("");
  const [procesando, setProcesando] = useState(false);

  const cargar = useCallback(async () => {
    const detalle = await api.obtener<RecepcionDetalle>(`/api/recepcion/solicitudes/${id}`);
    setSolicitud(detalle);
    setChecks(detalle.revision);
    setObservacion(detalle.revision.observacion);
  }, [id]);

  useEffect(() => { cargar().catch((error: Error) => setMensaje(error.message)); }, [cargar]);

  function marcar(requisito: string, campo: keyof Incidencia, valor: boolean | string) {
    setIncidencias((actual) => ({
      ...actual,
      [requisito]: {
        marcada: actual[requisito]?.marcada ?? false,
        observacion: actual[requisito]?.observacion ?? "",
        [campo]: valor,
      },
    }));
  }

  async function procesarRecepcion(recibirCompleta: boolean) {
    if (!solicitud) return;
    setProcesando(true);
    setMensaje("");
    const faltantes = Object.entries(incidencias)
      .filter(([, incidencia]) => incidencia.marcada)
      .map(([requisito, incidencia]) => ({ requisito, observacion: incidencia.observacion }));
    try {
      await api.enviarJson(`/api/recepcion/solicitudes/${id}/recibir`, {
        solicitud_completa: recibirCompleta && checks.solicitud_completa,
        documentos_legibles: recibirCompleta && checks.documentos_legibles,
        corresponden_al_programa: recibirCompleta && checks.corresponden_al_programa,
        observacion,
        faltantes,
      });
      await cargar();
      setMensaje(recibirCompleta ? "Recepción registrada y acuse generado." : "Se registraron los documentos faltantes.");
    } catch (error) {
      setMensaje((error as Error).message);
    } finally {
      setProcesando(false);
    }
  }

  if (!solicitud) return <div className="sprint2-page"><p>{mensaje || "Cargando expediente…"}</p></div>;
  const recibida = solicitud.estado === "recibida";
  const seleccionados = Object.values(incidencias).some((item) => item.marcada);
  const checklistCompleto = checks.solicitud_completa && checks.documentos_legibles && checks.corresponden_al_programa;

  return (
    <div className="sprint2-page recepcion-detalle-page">
      <Link href="/recepcion">← Solicitudes por recibir</Link>
      <p className="eyebrow">HU-07 · MK-07-2 · Delegación Regional Forestal</p>
      <h1>Revisión del expediente y acuse</h1>
      <p className="nota">{solicitud.programa} · {solicitud.municipio} · {solicitud.estado.replace("_", " ")}</p>
      {mensaje && <p className="s2-mensaje" role="status">{mensaje}</p>}

      <div className="s2-recepcion-columnas">
        <div className="s2-recepcion-izquierda">
          <Seccion titulo="Datos de la persona solicitante">
            <p><strong>{solicitud.nombre_solicitante}</strong><br />{solicitud.correo_solicitante}</p>
            <p>Enviada: {solicitud.enviada_en ? new Date(solicitud.enviada_en).toLocaleString("es-MX") : "—"}</p>
          </Seccion>
          <Seccion titulo="Solicitud Única (FO-PB-501)">
            <ListaDatos datos={solicitud.datos_501} />
          </Seccion>
          <Seccion titulo="Registro de Información (FO-PB-502)">
            <ListaDatos datos={solicitud.datos_502} />
          </Seccion>
          <Seccion titulo="Documentos presentados">
            {solicitud.documentos.filter((item) => item.aplica).map((documento) => {
              const incidencia = incidencias[documento.clave] ?? { marcada: false, observacion: "" };
              return <div className="s2-documento-revision" key={documento.clave}>
                <div>
                  <strong>{documento.numero ? `${documento.numero}. ` : ""}{documento.nombre}</strong>
                  <p>{documento.archivo_nombre ?? (documento.entregado ? "Capturado en formulario" : "Pendiente")}</p>
                  {documento.url_archivo && <a href={documento.url_archivo} target="_blank" rel="noreferrer">Ver / descargar archivo</a>}
                  {!documento.entregado && <span className="s2-etiqueta s2-error">Falta documento</span>}
                </div>
                {!recibida && documento.numero !== 3 && (
                  <div className="s2-incidencia">
                    <label className="s2-opcion">
                      <input type="checkbox" checked={incidencia.marcada}
                        onChange={(evento) => marcar(documento.clave, "marcada", evento.target.checked)} />
                      Falta / no cumple
                    </label>
                    {incidencia.marcada && <label className="s2-campo">
                      <span>Observación</span>
                      <textarea value={incidencia.observacion}
                        onChange={(evento) => marcar(documento.clave, "observacion", evento.target.value)} />
                    </label>}
                  </div>
                )}
              </div>;
            })}
          </Seccion>
          {!recibida && <Seccion titulo="Checklist de recepción">
            {([
              ["solicitud_completa", "Solicitud completa"],
              ["documentos_legibles", "Documentos legibles"],
              ["corresponden_al_programa", "Documentos corresponden al programa"],
            ] as const).map(([campo, etiqueta]) => (
              <label className="s2-opcion s2-checklist-recepcion" key={campo}>
                <input type="checkbox" checked={checks[campo]}
                  onChange={(evento) => setChecks((actual) => ({ ...actual, [campo]: evento.target.checked }))} />
                {etiqueta}
              </label>
            ))}
            <label className="s2-campo">
              <span>Observación general</span>
              <textarea value={observacion} onChange={(evento) => setObservacion(evento.target.value)} />
            </label>
            <div className="acciones">
              <button className="s2-boton primario" type="button" disabled={procesando || !checklistCompleto || seleccionados || !!solicitud.faltantes.length}
                onClick={() => void procesarRecepcion(true)}>Generar folio y acuse</button>
              {(!checklistCompleto || seleccionados || !!solicitud.faltantes.length) &&
                <button className="s2-boton secundario" type="button" disabled={procesando}
                  onClick={() => void procesarRecepcion(false)}>Registrar documentos faltantes</button>}
            </div>
          </Seccion>}
        </div>
        <Seccion titulo="Vista del acuse (PDF)">
          {solicitud.acuse_disponible
            ? <iframe className="s2-visor-acuse" title="Vista previa del acuse de recepción"
                src={`/api/recepcion/solicitudes/${id}/acuse/archivo`} />
            : <div className="s2-acuse-vacio">
                <strong>ACUSE DE RECEPCIÓN</strong>
                <p>Folio: {solicitud.folio ?? "Se asignará al recibir la solicitud"}</p>
                <p>El PDF se generará al completar la recepción.</p>
              </div>}
          {solicitud.acuse_disponible && <a className="s2-boton primario"
                href={`/api/recepcion/solicitudes/${id}/acuse/archivo`}
                download={`acuse-${solicitud.folio ?? id}.pdf`}>Descargar acuse (PDF)</a>}
        </Seccion>
      </div>
    </div>
  );
}

function Seccion({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  return <section className="s2-seccion"><h2>{titulo}</h2><div className="s2-seccion-contenido">{children}</div></section>;
}

function ListaDatos({ datos }: { datos: Record<string, unknown> }) {
  return <dl className="s2-lista-datos">
    {Object.entries(datos).filter(([, valor]) => valor !== "" && valor !== null && valor !== false)
      .map(([clave, valor]) => (
        <div key={clave}><dt>{clave.replaceAll("_", " ")}</dt><dd>{mostrar(valor)}</dd></div>
      ))}
  </dl>;
}

export default function RevisionRecepcionPage() {
  return <ProtegidaPorSesion><Contenido /></ProtegidaPorSesion>;
}
