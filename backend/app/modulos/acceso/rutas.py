"""HU-01 Acceso al sistema según rol y programa."""
from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.modulos.acceso.esquemas import BloqueInicioSalida, SesionSalida, SolicitudIngreso
from app.nucleo.base_datos import obtener_sesion
from app.nucleo.configuracion import obtener_configuracion
from app.servicios.autenticacion import servicio
from app.servicios.autenticacion.dependencias import poner_cookie_sesion, usuario_actual
from app.servicios.autenticacion.modelos import Usuario
from app.servicios.catalogo.servicio import region_por_id

router = APIRouter(prefix="/api/auth", tags=["HU-01 Acceso"])


def _armar_sesion(sesion: Session, solicitud: Request, usuario: Usuario) -> SesionSalida:
    permisos = servicio.permisos_de(usuario)
    # El menú completo lo registra main.py al arrancar; aquí solo se filtra por permisos.
    menu = [
        {"clave": o.clave, "etiqueta": o.etiqueta, "ruta": o.ruta}
        for o in solicitud.app.state.menu_completo
        if o.permiso is None or o.permiso in permisos
    ]
    bloques = [
        BloqueInicioSalida(
            clave=o.clave, titulo=o.titulo, descripcion=o.descripcion, ruta=o.ruta
        )
        for o in solicitud.app.state.bloques_inicio_completos
        if o.permiso is None or o.permiso in permisos
    ]
    region = region_por_id(sesion, usuario.region_id) if usuario.region_id else None
    apellidos = " ".join(p for p in (usuario.apellido_paterno, usuario.apellido_materno) if p)
    nombre_completo = " ".join(p for p in (usuario.nombre, apellidos) if p)
    return SesionSalida(
        nombre=usuario.nombre,
        apellido_paterno=usuario.apellido_paterno,
        apellido_materno=usuario.apellido_materno,
        nombre_completo=nombre_completo,
        correo=usuario.correo,
        rol={"clave": usuario.rol.clave, "nombre": usuario.rol.nombre},
        region={"id": region.id, "clave": region.clave, "nombre": region.nombre} if region else None,
        permisos=sorted(permisos), menu=menu, bloques=bloques,
        minutos_inactividad=obtener_configuracion().minutos_inactividad,
    )


@router.post("/ingresar", response_model=SesionSalida, summary="Iniciar sesión")
def ingresar(datos: SolicitudIngreso, respuesta: Response, solicitud: Request,
             sesion: Session = Depends(obtener_sesion)):
    usuario = servicio.autenticar(sesion, datos.correo, datos.contrasena)
    poner_cookie_sesion(respuesta, usuario.id)
    return _armar_sesion(sesion, solicitud, usuario)


@router.post("/salir", status_code=204, summary="Cerrar sesión")
def salir(respuesta: Response):
    respuesta.delete_cookie(obtener_configuracion().nombre_cookie_sesion, path="/")


@router.get("/yo", response_model=SesionSalida, summary="Persona con sesión, su rol, permisos y menú")
def yo(solicitud: Request, usuario: Usuario = Depends(usuario_actual),
       sesion: Session = Depends(obtener_sesion)):
    return _armar_sesion(sesion, solicitud, usuario)
