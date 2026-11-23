from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.modulos.recepcion.esquemas import RecepcionEntrada
from app.nucleo.base_datos import obtener_sesion
from app.servicios.autenticacion.dependencias import requiere_permiso
from app.servicios.autenticacion.modelos import Usuario
from app.servicios.requisitos.servicio import faltantes
from app.servicios.solicitudes import servicio
from app.servicios.solicitudes.modelos import Solicitud
from app.servicios.archivos.almacenamiento import ruta_de_archivo
from app.servicios.archivos.modelos import Archivo

router = APIRouter(prefix="/api/recepcion", tags=["Recepción"])
PERMISO = "solicitudes.recibir"


def _salida(sesion, solicitud):
    folio = servicio.folio_de(sesion, solicitud.id)
    return {
        "id": solicitud.id, "programa": solicitud.programa.nombre,
        "municipio": solicitud.municipio.nombre, "delegacion": solicitud.region.nombre,
        "estado": solicitud.estado, "folio": folio.valor if folio else None,
        "faltantes": faltantes(sesion, solicitud.id),
    }


@router.get("/solicitudes")
def listar(usuario: Usuario = Depends(requiere_permiso(PERMISO)),
           sesion: Session = Depends(obtener_sesion)):
    return [_salida(sesion, item) for item in servicio.listar_para_recepcion(sesion, usuario)]


@router.post("/solicitudes/{solicitud_id}/recibir")
def recibir(solicitud_id: int, entrada: RecepcionEntrada,
            usuario: Usuario = Depends(requiere_permiso(PERMISO)),
            sesion: Session = Depends(obtener_sesion)):
    solicitud = sesion.get(Solicitud, solicitud_id)
    if solicitud is None:
        from app.nucleo.excepciones import NoEncontrado
        raise NoEncontrado("La solicitud no existe.")
    servicio.recibir(sesion, solicitud, usuario, entrada.observacion)
    return _salida(sesion, solicitud)


@router.post("/solicitudes/{solicitud_id}/acuse")
def acuse(solicitud_id: int, usuario: Usuario = Depends(requiere_permiso(PERMISO)),
          sesion: Session = Depends(obtener_sesion)):
    solicitud = sesion.get(Solicitud, solicitud_id)
    if solicitud is None:
        from app.nucleo.excepciones import NoEncontrado
        raise NoEncontrado("La solicitud no existe.")
    acuse_generado = servicio.generar_acuse(sesion, solicitud, usuario)
    return {"id": acuse_generado.id, "archivo_id": acuse_generado.archivo_id,
            "url": f"/api/recepcion/solicitudes/{solicitud_id}/acuse/archivo"}


@router.get("/solicitudes/{solicitud_id}/acuse/archivo")
def archivo_acuse(solicitud_id: int, usuario: Usuario = Depends(requiere_permiso(PERMISO)),
                  sesion: Session = Depends(obtener_sesion)):
    solicitud = sesion.get(Solicitud, solicitud_id)
    if solicitud is None:
        from app.nucleo.excepciones import NoEncontrado
        raise NoEncontrado("La solicitud no existe.")
    registro = servicio.acuse_de(sesion, solicitud_id)
    archivo = sesion.get(Archivo, registro.archivo_id)
    return FileResponse(ruta_de_archivo(archivo), media_type=archivo.tipo_mime,
                        filename=archivo.nombre_original)
