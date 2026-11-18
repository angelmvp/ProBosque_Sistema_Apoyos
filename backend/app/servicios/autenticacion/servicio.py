"""Lógica de SRV-01: inicio de sesión, usuario actual y permisos."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.nucleo import seguridad
from app.nucleo.excepciones import AccesoDenegado, NoAutenticado
from app.servicios.autenticacion.modelos import Usuario
from app.servicios.bitacora import servicio as bitacora


def autenticar(sesion: Session, correo: str, contrasena: str) -> Usuario:
    """SRV-01.1. Mensaje genérico para no revelar si el correo existe."""
    usuario = sesion.scalar(select(Usuario).where(Usuario.correo == correo.strip().lower()))
    if usuario is None or not usuario.activo or not seguridad.verificar_contrasena(
        contrasena, usuario.hash_contrasena
    ):
        bitacora.registrar(
            sesion, accion="inicio_sesion", recurso="/api/auth/ingresar",
            resultado="fallido", detalle=f"correo={correo.strip().lower()}",
            usuario_id=usuario.id if usuario else None,
        )
        raise NoAutenticado("Usuario o contraseña incorrectos.")
    bitacora.registrar(sesion, accion="inicio_sesion", recurso="/api/auth/ingresar",
                       resultado="exitoso", usuario_id=usuario.id)
    return usuario


def usuario_por_id(sesion: Session, usuario_id: int) -> Usuario | None:
    usuario = sesion.get(Usuario, usuario_id)
    return usuario if usuario and usuario.activo else None


def permisos_de(usuario: Usuario) -> set[str]:
    """SRV-01.2: permisos efectivos de la persona según su rol."""
    return {p.clave for p in usuario.rol.permisos}


def exigir_permiso(sesion: Session, usuario: Usuario, permiso: str, recurso: str) -> None:
    """Niega el acceso y registra el intento en la bitácora (HU-01-CA-2)."""
    if permiso not in permisos_de(usuario):
        bitacora.registrar(
            sesion, accion="acceso_denegado", recurso=recurso, resultado="denegado",
            detalle=f"permiso requerido={permiso}; rol={usuario.rol.clave}", usuario_id=usuario.id,
        )
        # Se confirma el registro aunque la petición termine con error 403.
        sesion.commit()
        raise AccesoDenegado("No tienes permiso para realizar esta acción.")


__all__ = ["autenticar", "usuario_por_id", "permisos_de", "exigir_permiso", "NoAutenticado"]
