export type EstadoPrograma = "vigente" | "historica" | "sin_convocatoria";
export type EstadoPublicacion = "borrador" | "programada" | "vigente" | "historica";

export interface PublicacionResumen {
  id: number; titulo: string; vigencia_inicio: string; vigencia_fin: string;
  estado: EstadoPublicacion; url_pdf: string | null; url_visor: string | null;
  publicada_en: string | null; archivos: ArchivoPublicacion[];
}
export interface ArchivoPublicacion {
  id: number; tipo: TipoArchivo; nombre_tipo: string; etiqueta: string;
  nombre_original: string; extension: string; url: string;
}
export type TipoArchivo = "convocatoria" | "reglas_operacion" | "formato" | "anexo" | "otro";
export interface ProgramaPortal {
  clave: string; nombre: string; estado: EstadoPrograma; convocatoria_abierta: boolean;
  publicacion: PublicacionResumen | null; ultima_publicada: PublicacionResumen | null;
}
export interface Formato { clave: string; nombre: string; url: string }
export interface Delegacion {
  id: number; clave: string; nombre: string; descripcion: string; domicilio: string | null; telefono: string | null; horario: string | null;
}
export interface DetallePrograma extends ProgramaPortal { formatos: Formato[]; delegacion: Delegacion | null; municipio: Municipio | null }
export interface Region { id: number; clave: string; nombre: string }
export interface Municipio { id: number; nombre: string; region_id: number }
export interface PublicacionAdmin extends PublicacionResumen {
  programa_clave: string; programa_nombre: string; nombre_archivo: string | null;
}
export interface OpcionMenu { clave: string; etiqueta: string; ruta: string }
export interface Sesion {
  nombre: string; apellido_paterno: string; apellido_materno: string; nombre_completo: string;
  correo: string; rol: { clave: string; nombre: string };
  region: Region | null; permisos: string[]; menu: OpcionMenu[]; bloques: BloqueInicio[]; minutos_inactividad: number;
}
export interface BloqueInicio {
  clave: string; titulo: string; descripcion: string; ruta: string;
}
