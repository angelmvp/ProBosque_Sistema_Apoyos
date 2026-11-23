"""HU-02 Consulta pública de convocatorias (sin iniciar sesión)."""
from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.modulos.convocatorias import traductores
from app.modulos.convocatorias.esquemas import (
    DelegacionSalida, DetalleProgramaPortal, FormatoSalida, MunicipioSalida, ProgramaPortal, RegionSalida,
)
from app.nucleo.base_datos import obtener_sesion
from app.nucleo.excepciones import NoEncontrado
from app.servicios.archivos.almacenamiento import ruta_de_archivo
from app.servicios.catalogo import formatos, servicio as catalogo
from app.servicios.publicacion import servicio as publicaciones

router = APIRouter(prefix="/api/publico", tags=["HU-02 Consulta pública"])


@router.get("/regiones", response_model=list[RegionSalida], summary="Regiones (Delegaciones Regionales Forestales)")
def regiones(sesion: Session = Depends(obtener_sesion)):
    return catalogo.listar_regiones(sesion)


@router.get("/municipios", response_model=list[MunicipioSalida], summary="Municipios, opcionalmente de una región")
def municipios(region_id: int | None = None, sesion: Session = Depends(obtener_sesion)):
    return catalogo.listar_municipios(sesion, region_id)


@router.get("/programas", response_model=list[ProgramaPortal],
            summary="Programas con el estado de su convocatoria")
def programas(
    q: str | None = Query(default=None, description="Texto a buscar en el nombre del programa"),
    estado: str | None = Query(default=None, pattern="^(vigente|historica|sin_convocatoria)$"),
    sesion: Session = Depends(obtener_sesion),
):
    salida = []
    for programa in catalogo.listar_programas(sesion):
        if q and q.strip().lower() not in programa.nombre.lower():
            continue
        item = traductores.para_portal(programa, publicaciones.resumen_de_programa(sesion, programa.id))
        if estado and item.estado != estado:
            continue
        salida.append(item)
    return salida


@router.get("/programas/{clave}", response_model=DetalleProgramaPortal,
            summary="Detalle de un programa: convocatoria, formatos y delegación según municipio")
def detalle_programa(clave: str, municipio_id: int | None = None, sesion: Session = Depends(obtener_sesion)):
    programa = catalogo.programa_por_clave(sesion, clave)
    base = traductores.para_portal(programa, publicaciones.resumen_de_programa(sesion, programa.id))
    municipio = catalogo.municipio_por_id(sesion, municipio_id) if municipio_id else None
    return DetalleProgramaPortal(
        **base.model_dump(),
        formatos=[FormatoSalida(clave=f.clave, nombre=f.nombre, url=f"/api/publico/formatos/{f.clave}")
                  for f in formatos.formatos_de_programa(clave)],
        delegacion=DelegacionSalida.model_validate(municipio.region) if municipio else None,
        municipio=MunicipioSalida.model_validate(municipio) if municipio else None,
    )


@router.get("/delegacion", response_model=DelegacionSalida,
            summary="Delegación Regional Forestal que atiende a un municipio")
def delegacion(municipio_id: int, sesion: Session = Depends(obtener_sesion)):
    return catalogo.municipio_por_id(sesion, municipio_id).region


@router.get("/publicaciones/{publicacion_id}/pdf", summary="PDF de una publicación (visor)")
def pdf_publico(publicacion_id: int, sesion: Session = Depends(obtener_sesion)):
    publicacion = publicaciones.publicacion_publica(sesion, publicacion_id)
    relacion = next((r for r in publicacion.archivos if r.tipo == "convocatoria"), None)
    if relacion is None or not relacion.archivo.nombre_original.lower().endswith(".pdf"):
        raise NoEncontrado("La publicación no tiene una convocatoria PDF.")
    return FileResponse(ruta_de_archivo(relacion.archivo), media_type="application/pdf",
                        headers={"Content-Disposition": f'inline; filename="{relacion.archivo.nombre_original}"'})


@router.get("/publicaciones/{publicacion_id}/archivos/{archivo_id}", summary="Descargar o mostrar un archivo publicado")
def archivo_publico(publicacion_id: int, archivo_id: int, sesion: Session = Depends(obtener_sesion)):
    publicacion = publicaciones.publicacion_publica(sesion, publicacion_id)
    relacion = publicaciones.obtener_relacion(publicacion, archivo_id)
    archivo = relacion.archivo
    extension = archivo.nombre_original.lower()
    if extension.endswith(".pdf"):
        return FileResponse(ruta_de_archivo(archivo), media_type="application/pdf",
                            headers={"Content-Disposition": f'inline; filename="{archivo.nombre_original}"'})
    if extension.endswith(".docx"):
        media = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    elif extension.endswith(".xlsx"):
        media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        raise NoEncontrado("El tipo de archivo no está disponible.")
    return FileResponse(ruta_de_archivo(archivo), media_type=media,
                        filename=archivo.nombre_original)


@router.get("/formatos/{clave}", summary="Descargar un formato oficial (.docx)")
def descargar_formato(clave: str):
    ruta = formatos.ruta_formato(clave)
    if ruta is None:
        raise NoEncontrado("El formato no existe.")
    return FileResponse(ruta, filename=ruta.name,
                        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
