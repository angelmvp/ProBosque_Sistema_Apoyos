"use client";
import { ProtegidaPorSesion } from "@/compartido/ProtegidaPorSesion";
import { useSesion } from "@/modulos/acceso/ContextoSesion";

interface AccionPerfil {
  titulo: string;
  descripcion: string;
  disponible: boolean;
  ruta?: string;
}

function accionesDelRol(clave: string): AccionPerfil[] {
  const acciones: Record<string, AccionPerfil[]> = {
    solicitante: [
      { titulo: "Consultar convocatorias", descripcion: "Revisa programas y documentos disponibles.", disponible: true, ruta: "/" },
      { titulo: "Enviar solicitud de apoyo", descripcion: "La recepción de solicitudes se habilitará en una historia posterior.", disponible: false },
    ],
    delegacion_regional: [
      { titulo: "Expedientes de mi delegación", descripcion: "Consulta los expedientes asignados a tu región.", disponible: true, ruta: "/expedientes" },
      { titulo: "Solicitudes recibidas", descripcion: "La gestión de solicitudes recibidas se habilitará en una historia posterior.", disponible: false },
      { titulo: "Revisar documentación", descripcion: "La revisión documental se habilitará en una historia posterior.", disponible: false },
    ],
    direccion_general: [
      { titulo: "Publicaciones", descripcion: "Crea y administra convocatorias.", disponible: true, ruta: "/admin/publicaciones" },
      { titulo: "Todos los expedientes", descripcion: "Consulta expedientes de todas las delegaciones.", disponible: true, ruta: "/expedientes" },
      { titulo: "Asignar solicitudes", descripcion: "La asignación de solicitudes se habilitará en una historia posterior.", disponible: false },
    ],
    direccion_restauracion: [
      { titulo: "Dictámenes", descripcion: "Consulta la bandeja de dictámenes.", disponible: true, ruta: "/dictamenes" },
      { titulo: "Todos los expedientes", descripcion: "Consulta expedientes de todas las delegaciones.", disponible: true, ruta: "/expedientes" },
      { titulo: "Emitir dictamen", descripcion: "La emisión de dictámenes se habilitará en una historia posterior.", disponible: false },
    ],
  };
  return acciones[clave] ?? [];
}

function Contenido() {
  const { sesion } = useSesion();
  if (!sesion) return null;
  const acciones = accionesDelRol(sesion.rol.clave);
  const iniciales = sesion.nombre_completo.split(" ").map((parte) => parte[0]).join("").slice(0, 2).toUpperCase();
  return (
    <>
      <div className="perfil-encabezado">
        <div className="perfil-avatar" aria-hidden="true">{iniciales}</div>
        <div>
          <p className="etiqueta">Perfil de usuario</p>
          <h1>{sesion.nombre_completo}</h1>
          <p className="nota">{sesion.rol.nombre}{sesion.region ? ` · ${sesion.region.nombre}` : ""}</p>
        </div>
      </div>
      <div className="perfil-rejilla">
        <section className="tarjeta">
          <h2>Datos personales</h2>
          <dl className="datos-perfil">
            <dt>Nombre</dt><dd>{sesion.nombre}</dd>
            <dt>Apellido paterno</dt><dd>{sesion.apellido_paterno || "Por confirmar"}</dd>
            <dt>Apellido materno</dt><dd>{sesion.apellido_materno || "Por confirmar"}</dd>
            <dt>Correo</dt><dd>{sesion.correo}</dd>
          </dl>
        </section>
        <section className="tarjeta">
          <h2>Rol y alcance</h2>
          <dl className="datos-perfil">
            <dt>Rol</dt><dd>{sesion.rol.nombre}</dd>
            <dt>Delegación</dt><dd>{sesion.region?.nombre ?? "No aplica"}</dd>
            <dt>Permisos activos</dt><dd>{sesion.permisos.length}</dd>
          </dl>
          <p className="nota">Esta información es de solo lectura.</p>
        </section>
      </div>
      <section className="perfil-acciones">
        <h2>Acciones de tu rol</h2>
        <p className="nota">Las acciones futuras se muestran para indicar el alcance del rol.</p>
        <div className="rejilla">
          {acciones.map((accion) => accion.disponible ? (
            <a className="tarjeta accion-rol" href={accion.ruta} key={accion.titulo}>
              <strong>{accion.titulo}</strong><span>{accion.descripcion}</span>
            </a>
          ) : (
            <button className="tarjeta accion-rol accion-pendiente" type="button" disabled key={accion.titulo}>
              <strong>{accion.titulo}</strong><span>{accion.descripcion}</span><small>Historia todavía no implementada</small>
            </button>
          ))}
        </div>
      </section>
    </>
  );
}

export default function PaginaPerfil() {
  return <ProtegidaPorSesion><Contenido /></ProtegidaPorSesion>;
}
