"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState, type ChangeEvent, type FormEvent, type ReactNode } from "react";
import { api, ErrorApi } from "@/compartido/api";
import type { RequisitoSolicitud, Solicitud } from "@/compartido/tipos";
import { ProtegidaPorSesion } from "@/compartido/ProtegidaPorSesion";

type Persona = { nombre: string; primer_apellido: string; segundo_apellido: string };
type Datos501 = {
  folio_refrendo_2023: string; folio_refrendo_2024: string; folio_refrendo_2025: string;
  tipo_persona: string; tipo_persona_otro: string; denominacion: string;
  personas: { solicitante: Persona; secretario: Persona; tesorero: Persona; segunda_beneficiaria: Persona };
  grupos: string[]; predio_nombre: string; poblacion_localidad: string;
  pmf_vigente: string; cuenta_certificado: string; tipo_certificado: string;
  superficie_total: string; superficies: Record<string, string>;
  otro_programa_beneficiado: string; otro_programa_detalle: string;
  mantenimiento_navidena_anio: string; declaratoria_no_litigio: boolean;
};
type Datos502 = Record<string, string>;
type CampoError = { campo: string; mensaje: string };
type Concepto = { clave: string; nombre: string };
type ResumenPaso = {
  paso: number; completo: boolean; pendientes?: number; entregados?: number; total?: number;
  errores?: CampoError[]; faltantes?: string[];
};
type Resumen = { pasos: ResumenPaso[]; completo: boolean };

const GRUPOS = [
  "Mujeres / pueblos indígenas",
  "Personas que se autoreconocen como afromexicanas",
  "Personas con enfermedades crónico degenerativas",
  "Víctimas u ofendidas en delitos con perspectiva de género",
  "Personas repatriadas",
  "Mujeres cuidadoras de hijas e hijos menores de mujeres privadas de la libertad",
  "Ninguno",
];
const PASOS = [
  "Solicitud Única (FO-PB-501)",
  "Registro de Información (FO-PB-502)",
  "Documentos: identidad y representación",
  "Documentos: propiedad, posesión y requisitos",
  "Revisar y enviar",
];
const DECLARATORIA = "Bajo protesta de decir verdad, manifiesto que el predio descrito en esta solicitud, no presenta problemas de litigio de cualquier índole, ni gravamen, así mismo manifiesto que la documentación que se presenta no es apócrifa o falsa, ni se cuenta con problemas de representación, ni conflictos sociales, además de no tener como condicionante por parte de las autoridades en materia forestal, la restauración de la superficie que se propone, derivado de autorizaciones de aprovechamiento forestal, de cambio de uso del suelo o de cualquier otro tipo, así como pago por servicios ambientales por concepto de captura de carbono de otras dependencias gubernamentales o no gubernamentales.";
const AVISO_PRIVACIDAD = "Los datos personales recabados se incorporan a las bases de datos personales de los programas de PROBOSQUE 2026 para cumplir los requisitos de participación y dar seguimiento. La entrega de los datos es obligatoria; sin ellos no se puede atender el trámite. Se entiende consentimiento si no manifiesta disconformidad. Derechos ARCO: Unidad de Transparencia y UIPPE de PROBOSQUE, Metepec, Estado de México; texto completo en el formato FO-PB-502.";

function registro(valor: unknown): Record<string, unknown> {
  return valor && typeof valor === "object" && !Array.isArray(valor)
    ? valor as Record<string, unknown> : {};
}

function texto(valor: unknown): string {
  return typeof valor === "string" || typeof valor === "number" ? String(valor) : "";
}

function crearDatos501(valor: unknown): Datos501 {
  const datos = registro(valor);
  const personas = registro(datos.personas);
  const superficies = registro(datos.superficies);
  const persona = (clave: string): Persona => {
    const fila = registro(personas[clave]);
    return {
      nombre: texto(fila.nombre),
      primer_apellido: texto(fila.primer_apellido),
      segundo_apellido: texto(fila.segundo_apellido),
    };
  };
  const grupos = Array.isArray(datos.grupos)
    ? datos.grupos.filter((grupo): grupo is string => typeof grupo === "string") : [];
  return {
    folio_refrendo_2023: texto(datos.folio_refrendo_2023),
    folio_refrendo_2024: texto(datos.folio_refrendo_2024),
    folio_refrendo_2025: texto(datos.folio_refrendo_2025),
    tipo_persona: texto(datos.tipo_persona),
    tipo_persona_otro: texto(datos.tipo_persona_otro),
    denominacion: texto(datos.denominacion),
    personas: {
      solicitante: persona("solicitante"),
      secretario: persona("secretario"),
      tesorero: persona("tesorero"),
      segunda_beneficiaria: persona("segunda_beneficiaria"),
    },
    grupos,
    predio_nombre: texto(datos.predio_nombre),
    poblacion_localidad: texto(datos.poblacion_localidad),
    pmf_vigente: texto(datos.pmf_vigente),
    cuenta_certificado: texto(datos.cuenta_certificado),
    tipo_certificado: texto(datos.tipo_certificado),
    superficie_total: texto(datos.superficie_total),
    superficies: Object.fromEntries(Object.entries(superficies).map(([key, item]) => [key, texto(item)])),
    otro_programa_beneficiado: texto(datos.otro_programa_beneficiado),
    otro_programa_detalle: texto(datos.otro_programa_detalle),
    mantenimiento_navidena_anio: texto(datos.mantenimiento_navidena_anio),
    declaratoria_no_litigio: datos.declaratoria_no_litigio === true,
  };
}

function crearDatos502(valor: unknown): Datos502 {
  const datos = registro(valor);
  const campos = [
    "folio_refrendo_2023", "folio_refrendo_2024", "folio_refrendo_2025",
    "primer_apellido", "segundo_apellido", "nombres", "fecha_nacimiento", "sexo", "estado_civil",
    "grado_estudios", "tipo_identificacion", "folio_identificacion", "nacionalidad",
    "entidad_nacimiento", "curp", "telefono_fijo", "telefono_celular", "correo_electronico",
    "cuenta_red_social", "calle", "numero_exterior", "numero_interior", "colonia", "entre_calle",
    "y_calle", "otra_referencia", "localidad", "municipio", "entidad", "codigo_postal",
    "lugar_fecha", "nombre_beneficiario",
  ];
  return Object.fromEntries(campos.map((campo) => [campo, texto(datos[campo])]));
}

function Contenido() {
  const { id, numero } = useParams<{ id: string; numero: string }>();
  const router = useRouter();
  const paso = Math.min(5, Math.max(1, Number(numero) || 1));
  const [solicitud, setSolicitud] = useState<Solicitud | null>(null);
  const [datos501, setDatos501] = useState<Datos501>(crearDatos501(null));
  const [datos502, setDatos502] = useState<Datos502>(crearDatos502(null));
  const [aviso, setAviso] = useState(false);
  const [requisitos, setRequisitos] = useState<RequisitoSolicitud[]>([]);
  const [conceptos, setConceptos] = useState<Concepto[]>([]);
  const [resumen, setResumen] = useState<Resumen | null>(null);
  const [errores, setErrores] = useState<CampoError[]>([]);
  const [mensaje, setMensaje] = useState("");
  const [subiendo, setSubiendo] = useState("");
  const [guardando, setGuardando] = useState(false);

  const cargar = useCallback(async () => {
    const [detalle, listaRequisitos] = await Promise.all([
      api.obtener<Solicitud>(`/api/solicitudes/${id}`),
      api.obtener<RequisitoSolicitud[]>(`/api/solicitudes/${id}/requisitos`),
    ]);
    setSolicitud(detalle);
    const form501 = crearDatos501(detalle.datos_501);
    const form502 = crearDatos502(detalle.datos_502);
    const persona = form501.personas.solicitante;
    setDatos501(form501);
    setDatos502({
      ...form502,
      primer_apellido: form502.primer_apellido || persona.primer_apellido,
      segundo_apellido: form502.segundo_apellido || persona.segundo_apellido,
      nombres: form502.nombres || persona.nombre,
      folio_refrendo_2023: form502.folio_refrendo_2023 || form501.folio_refrendo_2023,
      folio_refrendo_2024: form502.folio_refrendo_2024 || form501.folio_refrendo_2024,
      folio_refrendo_2025: form502.folio_refrendo_2025 || form501.folio_refrendo_2025,
      municipio: form502.municipio || detalle.municipio,
      nombre_beneficiario: form502.nombre_beneficiario
        || [persona.nombre, persona.primer_apellido, persona.segundo_apellido].filter(Boolean).join(" "),
    });
    setAviso(detalle.aviso_privacidad);
    setRequisitos(listaRequisitos);
  }, [id]);

  useEffect(() => {
    cargar().catch((error: Error) => setMensaje(error.message));
  }, [cargar]);

  useEffect(() => {
    if (!solicitud || paso !== 1) return;
    api.obtener<Concepto[]>(`/api/solicitudes/catalogos/conceptos?programa=${solicitud.programa_clave}`)
      .then(setConceptos)
      .catch((error: Error) => setMensaje(error.message));
  }, [solicitud, paso]);

  useEffect(() => {
    if (paso !== 5) return;
    api.obtener<Resumen>(`/api/solicitudes/${id}/resumen`)
      .then(setResumen)
      .catch((error: Error) => setMensaje(error.message));
  }, [id, paso]);

  const editable = solicitud?.estado === "borrador";
  const erroresPorCampo = useMemo(() => new Map(errores.map((error) => [error.campo, error.mensaje])), [errores]);
  const prefijo = paso === 1 ? "datos_501." : "datos_502.";

  function actualizarPersona(persona: keyof Datos501["personas"], campo: keyof Persona, valor: string) {
    setDatos501((actual) => ({
      ...actual,
      personas: { ...actual.personas, [persona]: { ...actual.personas[persona], [campo]: valor } },
    }));
  }

  async function guardarActual(): Promise<void> {
    if (!editable) return;
    setGuardando(true);
    setErrores([]);
    try {
      const datos: { datos_501?: Datos501; datos_502?: Datos502; aviso_privacidad?: boolean } = {};
      if (paso === 1) datos.datos_501 = datos501;
      if (paso === 2) {
        datos.datos_502 = datos502;
        datos.aviso_privacidad = aviso;
      }
      if (datos.datos_501 || datos.datos_502) {
        await api.enviarJson(`/api/solicitudes/${id}`, datos, "PUT");
      }
      setMensaje("Borrador guardado.");
    } finally {
      setGuardando(false);
    }
  }

  async function continuar(evento?: FormEvent) {
    evento?.preventDefault();
    setMensaje("");
    setErrores([]);
    try {
      await guardarActual();
      if (paso < 5) {
        await api.accion(`/api/solicitudes/${id}/pasos/${paso}/validar`);
        router.push(`/solicitudes/${id}/paso/${paso + 1}`);
      } else {
        const enviada = await api.accion<Solicitud>(`/api/solicitudes/${id}/enviar`);
        router.push(`/solicitudes/${enviada.id}/confirmacion`);
      }
    } catch (error) {
      if (error instanceof ErrorApi) {
        setMensaje(error.message);
        setErrores(error.campos);
        const primera = error.campos[0]?.campo;
        if (primera) {
          window.setTimeout(() => {
            document.querySelector<HTMLElement>(`[data-campo="${CSS.escape(primera)}"]`)
              ?.scrollIntoView({ behavior: "smooth", block: "center" });
          }, 0);
        }
      } else {
        setMensaje((error as Error).message);
      }
    }
  }

  async function guardarBorrador() {
    try {
      await guardarActual();
    } catch (error) {
      setMensaje((error as Error).message);
    }
  }

  async function subirArchivo(requisito: string, evento: ChangeEvent<HTMLInputElement>) {
    const archivo = evento.target.files?.[0];
    if (!archivo) return;
    setSubiendo(requisito);
    setMensaje("");
    const formulario = new FormData();
    formulario.append("requisito", requisito);
    formulario.append("archivo", archivo);
    try {
      await api.enviarFormulario(`/api/solicitudes/${id}/documentos`, formulario);
      await cargar();
      setMensaje("Documento cargado correctamente.");
    } catch (error) {
      setMensaje((error as Error).message);
    } finally {
      setSubiendo("");
      evento.target.value = "";
    }
  }

  async function quitarArchivo(requisito: string) {
    try {
      await api.accion(`/api/solicitudes/${id}/documentos/${requisito}`, "DELETE");
      await cargar();
      setMensaje("Documento quitado.");
    } catch (error) {
      setMensaje((error as Error).message);
    }
  }

  if (!solicitud) {
    return <div className="sprint2-page"><p>{mensaje || "Cargando solicitud…"}</p></div>;
  }

  const titulo = PASOS[paso - 1];
  const requisitosPaso = requisitos.filter((item) => {
    if (paso === 3) return item.grupo === "identidad_representacion" && item.numero !== 3;
    if (paso === 4) return item.grupo === "propiedad_modalidad" || item.grupo === "programa";
    return false;
  });

  return (
    <div className="sprint2-page solicitud-asistente">
      <header className="s2-titulo-paso">
        <div>
          <p className="eyebrow">HU-04 · HU-05 · HU-06 · Rol: persona solicitante · Paso {paso} de 5</p>
          <h1>{titulo}</h1>
        </div>
        <span className={`s2-etiqueta ${editable ? "s2-aviso" : "s2-exito"}`}>
          {editable ? "Borrador sin enviar" : solicitud.estado}
        </span>
      </header>
      <nav className="s2-pasos" aria-label="Pasos de la solicitud">
        {PASOS.map((nombre, indice) => (
          <Link
            key={nombre}
            href={`/solicitudes/${id}/paso/${indice + 1}`}
            aria-current={paso === indice + 1 ? "step" : undefined}
            className={paso === indice + 1 ? "activo" : ""}
          >
            {indice + 1} · {nombre}
          </Link>
        ))}
      </nav>

      {mensaje && <p className={`s2-mensaje${errores.length ? " error" : ""}`} role="status">{mensaje}</p>}

      {paso === 1 && (
        <form className="s2-formulario-paso" onSubmit={(evento) => void continuar(evento)}>
          <Seccion titulo="Encabezado">
            <div className="s2-rejilla cuatro">
              <Campo etiqueta="Fecha de recepción" valor="Se asigna al recibir la solicitud" soloLectura />
              <Campo etiqueta="Folio del Programa 2026" valor="Borrador · sin folio" soloLectura />
              {[2023, 2024, 2025].map((anio) => {
                const clave = anio === 2023 ? "folio_refrendo_2023"
                  : anio === 2024 ? "folio_refrendo_2024" : "folio_refrendo_2025";
                return <Campo key={anio} etiqueta={`Folio de refrendo/mantenimiento ${anio}`}
                  valor={datos501[clave]} deshabilitado={!editable}
                  onChange={(valor) => setDatos501((actual) => ({ ...actual, [clave]: valor }))} />;
              })}
            </div>
          </Seccion>
          <Seccion titulo="I. Datos generales de la persona solicitante">
            <fieldset className="s2-campo-grupo" data-campo={`${prefijo}tipo_persona`}>
              <legend>I.1 Tipo de persona solicitante <Obligatorio /></legend>
              <div className="s2-opciones">
                {[
                  ["propietario", "Propietario"], ["poseedor", "Poseedor"],
                  ["nucleo_agrario", "Núcleo agrario"], ["sociedad", "Sociedad"], ["otro", "Otro"],
                ].map(([valor, etiqueta]) => (
                  <label className="s2-opcion" key={valor}>
                    <input type="radio" name="tipo_persona" value={valor}
                      checked={datos501.tipo_persona === valor} disabled={!editable}
                      onChange={() => setDatos501((actual) => ({ ...actual, tipo_persona: valor }))} />
                    {etiqueta}
                  </label>
                ))}
              </div>
              <ErrorCampo mensaje={erroresPorCampo.get(`${prefijo}tipo_persona`)} />
            </fieldset>
            {datos501.tipo_persona === "otro" && <Campo etiqueta="¿Cuál tipo de persona?"
              campo="datos_501.tipo_persona_otro" valor={datos501.tipo_persona_otro}
              error={erroresPorCampo.get("datos_501.tipo_persona_otro")} deshabilitado={!editable}
              onChange={(valor) => setDatos501((actual) => ({ ...actual, tipo_persona_otro: valor }))} />}
            {["nucleo_agrario", "sociedad"].includes(datos501.tipo_persona) && (
              <Campo etiqueta="I.2 Denominación o razón social" valor={datos501.denominacion}
                campo="datos_501.denominacion" error={erroresPorCampo.get("datos_501.denominacion")}
                deshabilitado={!editable}
                onChange={(valor) => setDatos501((actual) => ({ ...actual, denominacion: valor }))} />
            )}
            {([
              ["solicitante", "Persona solicitante / Presidente(a)"],
              ["secretario", "Secretario(a)"], ["tesorero", "Tesorero(a)"],
              ["segunda_beneficiaria", "Segunda persona beneficiaria"],
            ] as const).map(([clave, nombre]) => (
              <div className="s2-subseccion" key={clave}>
                <h3>{nombre}</h3>
                <div className="s2-rejilla tres">
                  {(["nombre", "primer_apellido", "segundo_apellido"] as const).map((campo) => (
                    <Campo key={campo} etiqueta={{
                      nombre: "Nombre(s)", primer_apellido: "Primer apellido",
                      segundo_apellido: "Segundo apellido",
                    }[campo]}
                      valor={datos501.personas[clave][campo]} deshabilitado={!editable}
                      campo={`datos_501.personas.${clave}.${campo}`}
                      error={erroresPorCampo.get(`datos_501.personas.${clave}.${campo}`)}
                      onChange={(valor) => actualizarPersona(clave, campo, valor)} />
                  ))}
                </div>
              </div>
            ))}
            <fieldset className="s2-campo-grupo" data-campo="datos_501.grupos">
              <legend>I.4 ¿La persona solicitante forma parte de alguno de estos grupos? <Obligatorio /></legend>
              <div className="s2-opciones">
                {GRUPOS.map((grupo) => (
                  <label className="s2-opcion" key={grupo}>
                    <input type="checkbox" checked={datos501.grupos.includes(grupo)} disabled={!editable}
                      onChange={(evento) => setDatos501((actual) => {
                        const grupos = grupo === "Ninguno"
                          ? (evento.target.checked ? [grupo] : [])
                          : evento.target.checked
                            ? [...actual.grupos.filter((item) => item !== "Ninguno"), grupo]
                            : actual.grupos.filter((item) => item !== grupo);
                        return { ...actual, grupos };
                      })} />
                    {grupo}
                  </label>
                ))}
              </div>
              <ErrorCampo mensaje={erroresPorCampo.get("datos_501.grupos")} />
            </fieldset>
          </Seccion>
          <Seccion titulo="II. Datos generales del predio">
            <div className="s2-rejilla dos">
              <Campo etiqueta="Nombre del predio (según documentación legal)" valor={datos501.predio_nombre}
                campo="datos_501.predio_nombre" error={erroresPorCampo.get("datos_501.predio_nombre")}
                deshabilitado={!editable}
                onChange={(valor) => setDatos501((actual) => ({ ...actual, predio_nombre: valor }))} />
              <Campo etiqueta="Municipio" valor={solicitud.municipio} soloLectura />
              <Campo etiqueta="Población o localidad" valor={datos501.poblacion_localidad}
                campo="datos_501.poblacion_localidad" error={erroresPorCampo.get("datos_501.poblacion_localidad")}
                deshabilitado={!editable}
                onChange={(valor) => setDatos501((actual) => ({ ...actual, poblacion_localidad: valor }))} />
              <Selector etiqueta="Predio con PMF vigente" valor={datos501.pmf_vigente}
                opciones={[["si", "Sí"], ["no", "No"]]} deshabilitado={!editable}
                onChange={(valor) => setDatos501((actual) => ({ ...actual, pmf_vigente: valor }))} />
              <Selector etiqueta="¿Cuenta con certificado?" valor={datos501.cuenta_certificado}
                opciones={[["si", "Sí"], ["no", "No"]]} deshabilitado={!editable}
                onChange={(valor) => setDatos501((actual) => ({ ...actual, cuenta_certificado: valor }))} />
              {datos501.cuenta_certificado === "si" && <Campo etiqueta="Tipo de certificado"
                valor={datos501.tipo_certificado} deshabilitado={!editable}
                campo="datos_501.tipo_certificado"
                error={erroresPorCampo.get("datos_501.tipo_certificado")}
                onChange={(valor) => setDatos501((actual) => ({ ...actual, tipo_certificado: valor }))} />}
            </div>
          </Seccion>
          <Seccion titulo={`III. Programa a solicitar · ${solicitud.programa}`}>
            <div className="s2-rejilla dos">
              <Campo etiqueta="Superficie total a incorporar (ha)" tipo="number" minimo="0.001"
                campo="datos_501.superficie_total" error={erroresPorCampo.get("datos_501.superficie_total")}
                valor={datos501.superficie_total} deshabilitado={!editable}
                onChange={(valor) => setDatos501((actual) => ({ ...actual, superficie_total: valor }))} />
            </div>
            <div className="s2-rejilla tres">
              {conceptos.map((concepto) => (
                <Campo key={concepto.clave} etiqueta={`${concepto.nombre} (ha)`} tipo="number" minimo="0"
                  campo={`datos_501.superficies.${concepto.clave}`}
                  error={erroresPorCampo.get(`datos_501.superficies.${concepto.clave}`)}
                  valor={datos501.superficies[concepto.clave] ?? ""} deshabilitado={!editable}
                  onChange={(valor) => setDatos501((actual) => ({
                    ...actual, superficies: { ...actual.superficies, [concepto.clave]: valor },
                  }))} />
              ))}
            </div>
            {solicitud.programa_clave === "plantaciones_sustentables" && (
              <div className="s2-rejilla dos">
                <Campo etiqueta="Año de establecimiento de plantación navideña"
                  valor={datos501.mantenimiento_navidena_anio} deshabilitado={!editable}
                  onChange={(valor) => setDatos501((actual) => ({ ...actual, mantenimiento_navidena_anio: valor }))} />
                <Selector etiqueta="¿El predio fue beneficiado por otro programa con el mismo propósito?"
                  valor={datos501.otro_programa_beneficiado} opciones={[["si", "Sí"], ["no", "No"]]}
                  deshabilitado={!editable}
                  onChange={(valor) => setDatos501((actual) => ({ ...actual, otro_programa_beneficiado: valor }))} />
                {datos501.otro_programa_beneficiado === "si" && <Campo
                  etiqueta="¿Cuál programa y dónde?" valor={datos501.otro_programa_detalle}
                  deshabilitado={!editable}
                  onChange={(valor) => setDatos501((actual) => ({ ...actual, otro_programa_detalle: valor }))} />}
              </div>
            )}
            <p className="s2-nota">Los conceptos de superficie son opcionales. Su suma no debe exceder la superficie total.</p>
          </Seccion>
          <Seccion titulo="Declaratoria de no litigio ni condicionante">
            <details className="s2-desplegable">
              <summary>Leer la declaratoria completa del formato FO-PB-501-A</summary>
              <p>{DECLARATORIA}</p>
            </details>
            <label className="s2-opcion s2-declaratoria" data-campo="datos_501.declaratoria_no_litigio">
              <input type="checkbox" checked={datos501.declaratoria_no_litigio} disabled={!editable}
                onChange={(evento) => setDatos501((actual) => ({
                  ...actual, declaratoria_no_litigio: evento.target.checked,
                }))} />
              Declaro bajo protesta de decir verdad que el predio no se encuentra en litigio ni tiene condicionante.
              <Obligatorio />
            </label>
            <ErrorCampo mensaje={erroresPorCampo.get("datos_501.declaratoria_no_litigio")} />
            <p className="s2-nota">El trámite es gratuito.</p>
          </Seccion>
          <Navegacion paso={paso} id={id} editable={!!editable} guardando={guardando}
            guardar={guardarBorrador} continuar={continuar} />
        </form>
      )}

      {paso === 2 && (
        <form className="s2-formulario-paso" onSubmit={(evento) => void continuar(evento)}>
          <Seccion titulo="Encabezado">
            <div className="s2-rejilla cuatro">
              <Campo etiqueta="Folio del programa 2026" valor="Se asigna al recibir" soloLectura />
              <Campo etiqueta="Fecha del alta en el Programa" valor="Se registra al enviar" soloLectura />
              {[2023, 2024, 2025].map((anio) => {
                const campo = `folio_refrendo_${anio}`;
                return <Campo key={anio} etiqueta={`Folio de refrendo/mantenimiento ${anio}`}
                  valor={datos502[campo]} deshabilitado={!editable}
                  onChange={(valor) => setDatos502((actual) => ({ ...actual, [campo]: valor }))} />;
              })}
            </div>
          </Seccion>
          <Seccion titulo="Datos de la persona solicitante y/o beneficiaria">
            <div className="s2-rejilla tres">
              {([
                ["primer_apellido", "Primer apellido"], ["segundo_apellido", "Segundo apellido"],
                ["nombres", "Nombre(s)"], ["fecha_nacimiento", "Fecha de nacimiento"],
                ["estado_civil", "Estado civil"], ["grado_estudios", "Grado de estudios"],
                ["tipo_identificacion", "Tipo de identificación oficial"],
                ["folio_identificacion", "Clave o folio del documento oficial"],
                ["nacionalidad", "Nacionalidad"], ["entidad_nacimiento", "Entidad de nacimiento"],
                ["curp", "Clave Única de Registro de Población (CURP)"],
                ["telefono_fijo", "Teléfono fijo (opcional)"],
                ["telefono_celular", "Teléfono celular"], ["correo_electronico", "Correo electrónico"],
                ["cuenta_red_social", "Cuenta de red social (opcional)"],
              ] as const).map(([campo, etiqueta]) => (
                <Campo key={campo} etiqueta={etiqueta} valor={datos502[campo]}
                  tipo={campo === "fecha_nacimiento" ? "date" : campo === "correo_electronico" ? "email" : "text"}
                  campo={`${prefijo}${campo}`} error={erroresPorCampo.get(`${prefijo}${campo}`)}
                  deshabilitado={!editable}
                  onChange={(valor) => setDatos502((actual) => ({ ...actual, [campo]: valor }))} />
              ))}
              <fieldset className="s2-campo-grupo" data-campo={`${prefijo}sexo`}>
                <legend>Sexo <Obligatorio /></legend>
                <div className="s2-opciones">
                  {[["H", "H = Hombre"], ["M", "M = Mujer"]].map(([valor, etiqueta]) => (
                    <label className="s2-opcion" key={valor}>
                      <input type="radio" name="sexo" value={valor} checked={datos502.sexo === valor}
                        disabled={!editable}
                        onChange={() => setDatos502((actual) => ({ ...actual, sexo: valor }))} />
                      {etiqueta}
                    </label>
                  ))}
                </div>
                <ErrorCampo mensaje={erroresPorCampo.get(`${prefijo}sexo`)} />
              </fieldset>
            </div>
            <p className="s2-nota">El formato indica que es obligatorio llenar todos los campos, corroborando la información con la identificación oficial o el comprobante de domicilio.</p>
          </Seccion>
          <Seccion titulo="Domicilio">
            <div className="s2-rejilla cuatro">
              {([
                ["calle", "Calle"], ["numero_exterior", "Número exterior"],
                ["numero_interior", "Número interior (opcional)"], ["colonia", "Colonia"],
                ["entre_calle", "Entre calle (opcional)"], ["y_calle", "Y calle (opcional)"],
                ["otra_referencia", "Otra referencia (opcional)"], ["localidad", "Localidad"],
                ["municipio", "Municipio"], ["entidad", "Entidad"], ["codigo_postal", "Código postal"],
              ] as const).map(([campo, etiqueta]) => (
                <Campo key={campo} etiqueta={etiqueta} valor={datos502[campo]}
                  campo={`${prefijo}${campo}`} error={erroresPorCampo.get(`${prefijo}${campo}`)}
                  deshabilitado={!editable}
                  onChange={(valor) => setDatos502((actual) => ({ ...actual, [campo]: valor }))} />
              ))}
            </div>
          </Seccion>
          <Seccion titulo="Aviso de privacidad">
            <p className="s2-nota">{AVISO_PRIVACIDAD}</p>
            <label className="s2-opcion">
              <input type="checkbox" checked={aviso} disabled={!editable}
                onChange={(evento) => setAviso(evento.target.checked)} />
              He leído el aviso de privacidad y autorizo el correo electrónico capturado para oír y recibir notificaciones.
              <Obligatorio />
            </label>
            <ErrorCampo mensaje={erroresPorCampo.get("aviso_privacidad")} />
            <div className="s2-rejilla dos">
              {([
                ["lugar_fecha", "Lugar y fecha de elaboración"],
                ["nombre_beneficiario", "Nombre de la persona solicitante y/o beneficiaria"],
              ] as const).map(([campo, etiqueta]) => (
                <Campo key={campo} etiqueta={etiqueta} valor={datos502[campo]}
                  campo={`${prefijo}${campo}`} error={erroresPorCampo.get(`${prefijo}${campo}`)}
                  deshabilitado={!editable}
                  onChange={(valor) => setDatos502((actual) => ({ ...actual, [campo]: valor }))} />
              ))}
            </div>
            <p className="s2-nota">La representación de la firma en el sistema está por confirmar. El trámite es gratuito.</p>
          </Seccion>
          <Navegacion paso={paso} id={id} editable={!!editable} guardando={guardando}
            guardar={guardarBorrador} continuar={continuar} />
        </form>
      )}

      {(paso === 3 || paso === 4) && (
        <div className="s2-formulario-paso">
          {paso === 3 && <Seccion titulo="Documentos a adjuntar (numeración del comprobante FO-PB-501-A)">
            {requisitosPaso.map((item) => (
              <FilaDocumento key={item.clave} item={item} editable={!!editable} subiendo={subiendo === item.clave}
                subir={(evento) => void subirArchivo(item.clave, evento)}
                quitar={() => void quitarArchivo(item.clave)} />
            ))}
            <p className="s2-nota">Los formatos y tamaños permitidos, así como los documentos que aplican según el tipo de persona, están por confirmar. Los refrendos pueden citar el folio del expediente en lugar de adjuntarse.</p>
          </Seccion>}
          {paso === 4 && <>
            <Seccion titulo="Documentos de propiedad o posesión">
              {requisitosPaso.filter((item) => item.grupo === "propiedad_modalidad").map((item) => (
                <FilaDocumento key={item.clave} item={item} editable={!!editable} subiendo={subiendo === item.clave}
                  subir={(evento) => void subirArchivo(item.clave, evento)}
                  quitar={() => void quitarArchivo(item.clave)} />
              ))}
            </Seccion>
            <Seccion titulo="Requisitos según el programa elegido en la Solicitud Única">
              {requisitosPaso.filter((item) => item.grupo === "programa" && item.aplica).map((item) => (
                <FilaDocumento key={item.clave} item={item} editable={!!editable} subiendo={subiendo === item.clave}
                  subir={(evento) => void subirArchivo(item.clave, evento)}
                  quitar={() => void quitarArchivo(item.clave)} />
              ))}
              {solicitud.programa_clave === "plantaciones_sustentables" &&
                <p className="s2-nota">Los requisitos específicos de Plantaciones Sustentables están por confirmar.</p>}
              <p className="s2-nota">El Registro de Información (documento 3) se llena en línea en el paso 2 y no se adjunta. Los documentos 1 a 8 aplican según el tipo de persona; los documentos 9 a 11 dependen del programa.</p>
            </Seccion>
          </>}
          <Navegacion paso={paso} id={id} editable={!!editable} guardando={guardando}
            guardar={guardarBorrador} continuar={continuar} />
        </div>
      )}

      {paso === 5 && (
        <div className="s2-formulario-paso">
          <Seccion titulo="Estado de cada parte de la solicitud">
            {resumen?.pasos.slice(0, 4).map((parte) => (
              <div className="s2-fila-resumen" key={parte.paso}>
                <span>{PASOS[parte.paso - 1]}</span>
                <span className="s2-resumen-detalle">
                  {parte.paso <= 2 ? `${parte.pendientes ?? 0} campos obligatorios pendientes`
                    : `${parte.entregados ?? 0} de ${parte.total ?? 0}`}
                </span>
                <span className={`s2-etiqueta ${parte.completo ? "s2-exito" : "s2-error"}`}>
                  {parte.completo ? "Completo" : "Incompleto"}
                </span>
                <Link href={`/solicitudes/${id}/paso/${parte.paso}`}>Editar</Link>
              </div>
            ))}
            {resumen && !resumen.completo && (
              <p className="s2-mensaje error">No se puede enviar mientras falten datos o documentos obligatorios.</p>
            )}
          </Seccion>
          <Navegacion paso={paso} id={id} editable={!!editable} guardando={guardando}
            guardar={guardarBorrador} continuar={continuar} deshabilitado={!editable || !resumen?.completo} />
        </div>
      )}
    </div>
  );
}

function Seccion({ titulo, children }: { titulo: string; children: ReactNode }) {
  return <section className="s2-seccion"><h2>{titulo}</h2><div className="s2-seccion-contenido">{children}</div></section>;
}

function Obligatorio() {
  return <span className="s2-obligatorio">Obligatorio</span>;
}

function ErrorCampo({ mensaje }: { mensaje?: string }) {
  return mensaje ? <span className="s2-error-campo">{mensaje}</span> : null;
}

function Campo({ etiqueta, valor, onChange, tipo = "text", minimo, campo, error, soloLectura, deshabilitado }:
  { etiqueta: string; valor: string; onChange?: (valor: string) => void; tipo?: string; minimo?: string;
    campo?: string; error?: string; soloLectura?: boolean; deshabilitado?: boolean }) {
  return (
    <label className="s2-campo" data-campo={campo}>
      <span>{etiqueta}</span>
      <input type={tipo} value={valor} min={minimo} readOnly={soloLectura} disabled={deshabilitado}
        aria-invalid={!!error} onChange={(evento) => onChange?.(evento.target.value)} />
      <ErrorCampo mensaje={error} />
    </label>
  );
}

function Selector({ etiqueta, valor, opciones, onChange, deshabilitado }:
  { etiqueta: string; valor: string; opciones: [string, string][]; onChange: (valor: string) => void;
    deshabilitado?: boolean }) {
  return (
    <label className="s2-campo">
      <span>{etiqueta}</span>
      <select value={valor} disabled={deshabilitado} onChange={(evento) => onChange(evento.target.value)}>
        <option value="">Selecciona una opción</option>
        {opciones.map(([clave, nombre]) => <option key={clave} value={clave}>{nombre}</option>)}
      </select>
    </label>
  );
}

function FilaDocumento({ item, editable, subiendo, subir, quitar }:
  { item: RequisitoSolicitud; editable: boolean; subiendo: boolean;
    subir: (evento: ChangeEvent<HTMLInputElement>) => void; quitar: () => void }) {
  const estado = subiendo ? "Subiendo…" : item.entregado ? "Cargado"
    : item.aplica ? "Pendiente" : "No aplica para tu tipo de persona";
  const bytes = item.archivo_tamano ? `${(item.archivo_tamano / 1024 / 1024).toFixed(2)} MB` : "";
  return (
    <div className={`s2-fila-documento${item.aplica ? "" : " no-aplica"}`}>
      <span className="s2-numero">{item.numero ?? "·"}</span>
      <div className="s2-documento-nombre">
        <strong>{item.nombre}</strong>
        {item.descripcion && <span>{item.descripcion}</span>}
        {item.archivo_nombre && <span>{item.archivo_nombre} · {bytes}</span>}
        {item.observacion && <span className="s2-motivo">{item.observacion}</span>}
        {item.entregado && item.url_archivo && <span className="acciones">
          <a href={item.url_archivo} target="_blank" rel="noreferrer">Ver / descargar</a>
          {editable && <button className="s2-enlace" type="button" onClick={quitar}>Quitar</button>}
        </span>}
      </div>
      <div className="s2-selector-archivo">
        {item.aplica && editable && <label className="s2-boton-archivo">
          {item.entregado ? "Reemplazar archivo" : "Seleccionar archivo"}
          <input type="file" accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png"
            disabled={subiendo} onChange={subir} />
        </label>}
        {item.aplica && editable && <span>PDF, JPG o PNG · máximo 10 MB</span>}
      </div>
      <span className={`s2-etiqueta ${!item.aplica ? "s2-neutro" : item.entregado || subiendo ? "s2-exito" : "s2-aviso"}`}>
        {estado}
      </span>
    </div>
  );
}

function Navegacion({ paso, id, editable, guardando, guardar, continuar, deshabilitado = false }:
  { paso: number; id: string; editable: boolean; guardando: boolean; guardar: () => void;
    continuar: () => void; deshabilitado?: boolean }) {
  const anterior = paso === 1 ? "/solicitudes" : `/solicitudes/${id}/paso/${paso - 1}`;
  return (
    <div className="s2-navegacion">
      <div className="s2-navegacion-izquierda">
        {paso === 1 && <Link className="s2-boton secundario" href="/solicitudes">Cancelar</Link>}
        <Link className="s2-boton secundario" href={anterior}>← Anterior</Link>
      </div>
      <div className="s2-navegacion-derecha">
        {editable && <button className="s2-boton secundario" type="button" disabled={guardando}
          onClick={guardar}>{guardando ? "Guardando…" : "Guardar borrador"}</button>}
        {editable && <button className="s2-boton primario" type="button"
          disabled={guardando || deshabilitado} onClick={() => void continuar()}>
          {paso === 5 ? "Enviar solicitud y obtener acuse →" : "Guardar y continuar →"}
        </button>}
      </div>
    </div>
  );
}

export default function PasoSolicitud() {
  return <ProtegidaPorSesion><Contenido /></ProtegidaPorSesion>;
}
