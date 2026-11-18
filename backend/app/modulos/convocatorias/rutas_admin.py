"""HU-03 Gestión de publicaciones (rol: Dirección General de PROBOSQUE)."""
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.modulos.convocatorias import traductores
from app.modulos.convocatorias.esquemas import PublicacionAdmin
from app.nucleo.base_datos import obtener_sesion
from app.nucleo.excepciones import DatosInvalidos, NoEncontrado
from app.servicios.archivos.almacenamiento import ruta_de_archivo
from app.servicios.autenticacion.dependencias import requiere_permiso
from app.servicios.autenticacion.modelos import Usuario
from app.servicios.publicacion import servicio

PERMISO = "publicaciones.gestionar"
router = APIRouter(prefix="/api/publicaciones", tags=["HU-03 Publicaciones"])


async def _leer_pdf(archivo: UploadFile | None) -> tuple[str | None, bytes | None]:
    if archivo is None or not archivo.filename:
        return None, None
    return archivo.filename, await archivo.read()


def _accion(accion: str) -> bool:
    if accion not in ("borrador", "publicar"):
        raise DatosInvalidos("La acción debe ser «borrador» o «publicar».")
    return accion == "publicar"


@router.get("", response_model=list[PublicacionAdmin], summary="Listar publicaciones")
def listar(programa: str | None = None, usuario: Usuario = Depends(requiere_permiso(PERMISO)),
           sesion: Session = Depends(obtener_sesion)):
    return [traductores.para_admin(p) for p in servicio.listar(sesion, programa)]


@router.post("", response_model=PublicacionAdmin, status_code=201,
             summary="Crear una publicación como borrador o publicarla")
async def crear(
    programa: Annotated[str, Form()], titulo: Annotated[str, Form()],
    vigencia_inicio: Annotated[date, Form()], vigencia_fin: Annotated[date, Form()],
    accion: Annotated[str, Form()] = "borrador", archivo: UploadFile | None = File(default=None),
    usuario: Usuario = Depends(requiere_permiso(PERMISO)), sesion: Session = Depends(obtener_sesion),
):
    publicar = _accion(accion)
    nombre, contenido = await _leer_pdf(archivo)
    p = servicio.crear(sesion, usuario_id=usuario.id, programa_clave=programa, titulo=titulo,
                       vigencia_inicio=vigencia_inicio, vigencia_fin=vigencia_fin,
                       nombre_pdf=nombre, contenido_pdf=contenido, publicar=publicar)
    return traductores.para_admin(p)


@router.get("/{publicacion_id}", response_model=PublicacionAdmin, summary="Ver una publicación")
def ver(publicacion_id: int, usuario: Usuario = Depends(requiere_permiso(PERMISO)),
        sesion: Session = Depends(obtener_sesion)):
    return traductores.para_admin(servicio.obtener(sesion, publicacion_id))


@router.put("/{publicacion_id}", response_model=PublicacionAdmin, summary="Editar un borrador")
async def editar(
    publicacion_id: int, programa: Annotated[str, Form()], titulo: Annotated[str, Form()],
    vigencia_inicio: Annotated[date, Form()], vigencia_fin: Annotated[date, Form()],
    accion: Annotated[str, Form()] = "borrador", archivo: UploadFile | None = File(default=None),
    usuario: Usuario = Depends(requiere_permiso(PERMISO)), sesion: Session = Depends(obtener_sesion),
):
    publicar = _accion(accion)
    nombre, contenido = await _leer_pdf(archivo)
    p = servicio.actualizar_borrador(
        sesion, publicacion_id, usuario_id=usuario.id, programa_clave=programa, titulo=titulo,
        vigencia_inicio=vigencia_inicio, vigencia_fin=vigencia_fin, nombre_pdf=nombre,
        contenido_pdf=contenido, publicar=publicar)
    return traductores.para_admin(p)


@router.post("/{publicacion_id}/publicar", response_model=PublicacionAdmin, summary="Publicar un borrador")
def publicar(publicacion_id: int, usuario: Usuario = Depends(requiere_permiso(PERMISO)),
             sesion: Session = Depends(obtener_sesion)):
    return traductores.para_admin(servicio.publicar_borrador(sesion, publicacion_id, usuario.id))


@router.delete("/{publicacion_id}", status_code=204, summary="Eliminar un borrador (lo publicado no se elimina)")
def eliminar(publicacion_id: int, usuario: Usuario = Depends(requiere_permiso(PERMISO)),
             sesion: Session = Depends(obtener_sesion)):
    servicio.eliminar_borrador(sesion, publicacion_id)


@router.get("/{publicacion_id}/pdf", summary="PDF de una publicación (también borradores)")
def pdf(publicacion_id: int, usuario: Usuario = Depends(requiere_permiso(PERMISO)),
        sesion: Session = Depends(obtener_sesion)):
    p = servicio.obtener(sesion, publicacion_id)
    if p.archivo is None:
        raise NoEncontrado("La publicación no tiene archivo.")
    return FileResponse(ruta_de_archivo(p.archivo), media_type="application/pdf",
                        headers={"Content-Disposition": f'inline; filename="{p.archivo.nombre_original}"'})
