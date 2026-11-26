from datetime import date

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modulos.recepcion.esquemas import RecepcionEntrada
from app.nucleo.base_datos import obtener_sesion
from app.nucleo.excepciones import AccesoDenegado, NoEncontrado
from app.servicios.archivos.almacenamiento import ruta_de_archivo
from app.servicios.archivos.modelos import Archivo
from app.servicios.autenticacion.dependencias import requiere_permiso
from app.servicios.autenticacion.modelos import Usuario
from app.servicios.requisitos.servicio import checklist, faltantes
from app.servicios.solicitudes import servicio
from app.servicios.solicitudes.modelos import Acuse, Recepcion, Solicitud

router = APIRouter(prefix="/api/recepcion", tags=["Recepción"])
PERMISO = "solicitudes.recibir"


def _datos_solicitud(sesion: Session, solicitud: Solicitud) -> dict:
    docs = checklist(
        sesion, solicitud.id, solicitud.programa.clave,
        (solicitud.datos_501 or {}).get("tipo_persona", ""), solicitud.datos_501,
    )
    persona = solicitud.solicitante
    nombre = " ".join(filter(None, [
        persona.nombre, persona.apellido_paterno, persona.apellido_materno,
    ]))
    folio = servicio.folio_de(sesion, solicitud.id)
    acuse = sesion.scalar(select(Acuse.id).where(Acuse.solicitud_id == solicitud.id))
    for documento in docs:
        if documento["url_archivo"]:
            documento["url_archivo"] = (
                f"/api/recepcion/solicitudes/{solicitud.id}/documentos/"
                f"{documento['clave']}/archivo"
            )
    return {
        "id": solicitud.id,
        "programa": solicitud.programa.nombre,
        "programa_clave": solicitud.programa.clave,
        "municipio": solicitud.municipio.nombre,
        "delegacion": solicitud.region.nombre,
        "estado": solicitud.estado,
        "folio": folio.valor if folio else None,
        "enviada_en": solicitud.enviada_en,
        "recibida_en": solicitud.recibida_en,
        "nombre_solicitante": nombre,
        "correo_solicitante": persona.correo,
        "datos_501": solicitud.datos_501 or {},
        "datos_502": solicitud.datos_502 or {},
        "aviso_privacidad": solicitud.aviso_privacidad,
        "documentos": docs,
        "faltantes": faltantes(
            sesion, solicitud.id, solicitud.programa.clave,
            (solicitud.datos_501 or {}).get("tipo_persona", ""), solicitud.datos_501,
        ),
        "acuse_disponible": acuse is not None,
    }


@router.get("/solicitudes")
def listar(programa: str | None = None, estado: str | None = None,
           municipio: str | None = None, fecha_desde: date | None = None,
           fecha_hasta: date | None = None,
           usuario: Usuario = Depends(requiere_permiso(PERMISO)),
           sesion: Session = Depends(obtener_sesion)):
    solicitudes = servicio.listar_para_recepcion(sesion, usuario)
    if programa:
        solicitudes = [s for s in solicitudes if s.programa.clave == programa]
    if estado:
        solicitudes = [s for s in solicitudes if s.estado == estado]
    if municipio:
        solicitudes = [s for s in solicitudes if municipio.casefold() in s.municipio.nombre.casefold()]
    if fecha_desde:
        solicitudes = [s for s in solicitudes if s.enviada_en and s.enviada_en.date() >= fecha_desde]
    if fecha_hasta:
        solicitudes = [s for s in solicitudes if s.enviada_en and s.enviada_en.date() <= fecha_hasta]
    return [_datos_solicitud(sesion, solicitud) for solicitud in solicitudes]


@router.get("/solicitudes/{solicitud_id}")
def detalle(solicitud_id: int, usuario: Usuario = Depends(requiere_permiso(PERMISO)),
            sesion: Session = Depends(obtener_sesion)):
    solicitud = sesion.get(Solicitud, solicitud_id)
    if solicitud is None:
        raise NoEncontrado("La solicitud no existe.")
    if usuario.region_id is not None and solicitud.region_id != usuario.region_id:
        raise AccesoDenegado("La solicitud no pertenece a tu delegación.")
    resultado = _datos_solicitud(sesion, solicitud)
    revision = sesion.scalar(select(Recepcion).where(Recepcion.solicitud_id == solicitud.id))
    resultado["revision"] = {
        "observacion": revision.observacion if revision else "",
        "solicitud_completa": revision.solicitud_completa if revision else False,
        "documentos_legibles": revision.documentos_legibles if revision else False,
        "corresponden_al_programa": revision.corresponden_al_programa if revision else False,
    }
    return resultado


@router.get("/solicitudes/{solicitud_id}/documentos/{requisito}/archivo")
def descargar_documento(solicitud_id: int, requisito: str,
                        usuario: Usuario = Depends(requiere_permiso(PERMISO)),
                        sesion: Session = Depends(obtener_sesion)):
    solicitud = sesion.get(Solicitud, solicitud_id)
    if solicitud is None:
        raise NoEncontrado("La solicitud no existe.")
    if usuario.region_id is not None and solicitud.region_id != usuario.region_id:
        raise AccesoDenegado("La solicitud no pertenece a tu delegación.")
    documento = next((item for item in _datos_solicitud(sesion, solicitud)["documentos"]
                      if item["clave"] == requisito and item["archivo_id"]), None)
    if documento is None:
        raise NoEncontrado("El documento no está disponible.")
    archivo = sesion.get(Archivo, documento["archivo_id"])
    return FileResponse(ruta_de_archivo(archivo), media_type=archivo.tipo_mime,
                        filename=archivo.nombre_original)


@router.post("/solicitudes/{solicitud_id}/recibir")
def recibir(solicitud_id: int, entrada: RecepcionEntrada,
            usuario: Usuario = Depends(requiere_permiso(PERMISO)),
            sesion: Session = Depends(obtener_sesion)):
    solicitud = sesion.get(Solicitud, solicitud_id)
    if solicitud is None:
        raise NoEncontrado("La solicitud no existe.")
    servicio.recibir(
        sesion, solicitud, usuario, observacion=entrada.observacion,
        solicitud_completa=entrada.solicitud_completa,
        documentos_legibles=entrada.documentos_legibles,
        corresponden_al_programa=entrada.corresponden_al_programa,
        documentos_faltantes=[item.model_dump() for item in entrada.faltantes],
    )
    return _datos_solicitud(sesion, solicitud)


@router.post("/solicitudes/{solicitud_id}/acuse")
def acuse(solicitud_id: int, usuario: Usuario = Depends(requiere_permiso(PERMISO)),
          sesion: Session = Depends(obtener_sesion)):
    solicitud = sesion.get(Solicitud, solicitud_id)
    if solicitud is None:
        raise NoEncontrado("La solicitud no existe.")
    if usuario.region_id is not None and solicitud.region_id != usuario.region_id:
        raise AccesoDenegado("La solicitud no pertenece a tu delegación.")
    acuse_generado = servicio.generar_acuse(sesion, solicitud, usuario)
    return {"id": acuse_generado.id, "archivo_id": acuse_generado.archivo_id,
            "url": f"/api/recepcion/solicitudes/{solicitud_id}/acuse/archivo"}


@router.get("/solicitudes/{solicitud_id}/acuse/archivo")
def archivo_acuse(solicitud_id: int, usuario: Usuario = Depends(requiere_permiso(PERMISO)),
                  sesion: Session = Depends(obtener_sesion)):
    solicitud = sesion.get(Solicitud, solicitud_id)
    if solicitud is None:
        raise NoEncontrado("La solicitud no existe.")
    if usuario.region_id is not None and solicitud.region_id != usuario.region_id:
        raise AccesoDenegado("La solicitud no pertenece a tu delegación.")
    registro = servicio.acuse_de(sesion, solicitud_id)
    archivo = sesion.get(Archivo, registro.archivo_id)
    return FileResponse(
        ruta_de_archivo(archivo), media_type=archivo.tipo_mime,
        headers={"Content-Disposition": "inline"},
    )
