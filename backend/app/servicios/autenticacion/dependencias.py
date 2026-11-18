"""Dependencias de FastAPI para proteger rutas. Se usan desde cualquier módulo."""
from fastapi import Cookie, Depends, Response
from sqlalchemy.orm import Session

from app.nucleo import seguridad
from app.nucleo.base_datos import obtener_sesion
from app.nucleo.configuracion import obtener_configuracion
from app.nucleo.excepciones import NoAutenticado
from app.servicios.autenticacion import servicio
from app.servicios.autenticacion.modelos import Usuario


def poner_cookie_sesion(respuesta: Response, usuario_id: int) -> None:
    cfg = obtener_configuracion()
    respuesta.set_cookie(
        cfg.nombre_cookie_sesion, seguridad.crear_token(usuario_id),
        max_age=cfg.minutos_inactividad * 60, httponly=True, samesite="lax",
        secure=cfg.cookie_segura, path="/",
    )


def usuario_actual(
    respuesta: Response,
    sesion: Session = Depends(obtener_sesion),
    token: str | None = Cookie(default=None, alias=obtener_configuracion().nombre_cookie_sesion),
) -> Usuario:
    """Persona con sesión activa. Cada petición renueva el plazo de inactividad."""
    usuario_id = seguridad.leer_token(token) if token else None
    usuario = servicio.usuario_por_id(sesion, usuario_id) if usuario_id else None
    if usuario is None:
        raise NoAutenticado("Tu sesión no es válida o expiró. Inicia sesión de nuevo.")
    poner_cookie_sesion(respuesta, usuario.id)
    return usuario


def requiere_permiso(permiso: str):
    """Uso: `usuario = Depends(requiere_permiso("publicaciones.gestionar"))`.
    Si falta el permiso responde 403 y deja registro en la bitácora."""
    def dependencia(
        usuario: Usuario = Depends(usuario_actual),
        sesion: Session = Depends(obtener_sesion),
    ) -> Usuario:
        servicio.exigir_permiso(sesion, usuario, permiso, recurso=f"permiso:{permiso}")
        return usuario
    return dependencia
