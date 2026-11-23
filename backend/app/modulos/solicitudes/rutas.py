from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.modulos.solicitudes.esquemas import FormularioSolicitud, SolicitudCrear, SolicitudSalida
from app.nucleo.base_datos import obtener_sesion
from app.nucleo.excepciones import DatosInvalidos
from app.servicios.autenticacion.dependencias import requiere_permiso
from app.servicios.autenticacion.modelos import Usuario
from app.servicios.requisitos.servicio import checklist, faltantes
from app.servicios.archivos.almacenamiento import ruta_de_archivo
from app.servicios.archivos.modelos import Archivo
from app.servicios.solicitudes.modelos import Acuse
from app.servicios.catalogo import servicio as catalogo
from app.servicios.solicitudes import servicio

router = APIRouter(prefix="/api/solicitudes", tags=["Solicitudes"])
PERMISO = "solicitudes.gestionar_propias"


def _salida(sesion: Session, solicitud) -> SolicitudSalida:
    folio = servicio.folio_de(sesion, solicitud.id)
    return SolicitudSalida(id=solicitud.id, programa=solicitud.programa.nombre,
                           municipio=solicitud.municipio.nombre, delegacion=solicitud.region.nombre,
                           estado=solicitud.estado, creada_en=solicitud.creada_en,
                           enviada_en=solicitud.enviada_en, recibida_en=solicitud.recibida_en,
                           folio=folio.valor if folio else None, faltantes=faltantes(sesion, solicitud.id))


@router.get("", response_model=list[SolicitudSalida])
def listar(usuario: Usuario = Depends(requiere_permiso(PERMISO)),
           sesion: Session = Depends(obtener_sesion)):
    return [_salida(sesion, item) for item in servicio.listar_propias(sesion, usuario)]


@router.get("/catalogos/programas")
def programas(usuario: Usuario = Depends(requiere_permiso(PERMISO)),
              sesion: Session = Depends(obtener_sesion)):
    return [{"id": programa.id, "clave": programa.clave, "nombre": programa.nombre}
            for programa in catalogo.listar_programas(sesion) if programa.solicitud_en_linea]


@router.get("/catalogos/municipios")
def municipios(usuario: Usuario = Depends(requiere_permiso(PERMISO)),
               sesion: Session = Depends(obtener_sesion)):
    return [{"id": municipio.id, "nombre": municipio.nombre, "region_id": municipio.region_id}
            for municipio in catalogo.listar_municipios(sesion)]


@router.post("", response_model=SolicitudSalida, status_code=201)
def crear(entrada: SolicitudCrear, usuario: Usuario = Depends(requiere_permiso(PERMISO)),
          sesion: Session = Depends(obtener_sesion)):
    return _salida(sesion, servicio.crear(sesion, usuario, entrada.programa_id, entrada.municipio_id))


@router.get("/{solicitud_id}", response_model=SolicitudSalida)
def detalle(solicitud_id: int, usuario: Usuario = Depends(requiere_permiso(PERMISO)),
            sesion: Session = Depends(obtener_sesion)):
    return _salida(sesion, servicio.exigir_propietario(sesion, solicitud_id, usuario))


@router.put("/{solicitud_id}", response_model=SolicitudSalida)
def actualizar(solicitud_id: int, entrada: FormularioSolicitud,
               usuario: Usuario = Depends(requiere_permiso(PERMISO)),
               sesion: Session = Depends(obtener_sesion)):
    solicitud = servicio.exigir_propietario(sesion, solicitud_id, usuario)
    return _salida(sesion, servicio.actualizar_formulario(
        sesion, solicitud, datos_501=entrada.datos_501, datos_502=entrada.datos_502,
        aviso_privacidad=entrada.aviso_privacidad))


@router.post("/{solicitud_id}/documentos", response_model=SolicitudSalida)
async def documento(solicitud_id: int, requisito: str = Form(...),
                    archivo: UploadFile = File(...),
                    usuario: Usuario = Depends(requiere_permiso(PERMISO)),
                    sesion: Session = Depends(obtener_sesion)):
    solicitud = servicio.exigir_propietario(sesion, solicitud_id, usuario)
    contenido = await archivo.read()
    if not contenido:
        raise DatosInvalidos("El archivo está vacío.")
    servicio.agregar_documento(sesion, solicitud, requisito, archivo.filename or "documento",
                               contenido, usuario)
    return _salida(sesion, solicitud)


@router.get("/{solicitud_id}/requisitos")
def requisitos(solicitud_id: int, usuario: Usuario = Depends(requiere_permiso(PERMISO)),
               sesion: Session = Depends(obtener_sesion)):
    servicio.exigir_propietario(sesion, solicitud_id, usuario)
    return checklist(sesion, solicitud_id)


@router.delete("/{solicitud_id}/documentos/{requisito}")
def quitar_documento(solicitud_id: int, requisito: str,
                     usuario: Usuario = Depends(requiere_permiso(PERMISO)),
                     sesion: Session = Depends(obtener_sesion)):
    solicitud = servicio.exigir_propietario(sesion, solicitud_id, usuario)
    servicio.quitar_documento(sesion, solicitud, requisito, usuario)
    return _salida(sesion, solicitud)


@router.post("/{solicitud_id}/enviar", response_model=SolicitudSalida)
def enviar(solicitud_id: int, usuario: Usuario = Depends(requiere_permiso(PERMISO)),
           sesion: Session = Depends(obtener_sesion)):
    solicitud = servicio.exigir_propietario(sesion, solicitud_id, usuario)
    return _salida(sesion, servicio.enviar(sesion, solicitud, usuario))


@router.get("/{solicitud_id}/acuse")
def acuse(solicitud_id: int, usuario: Usuario = Depends(requiere_permiso(PERMISO)),
          sesion: Session = Depends(obtener_sesion)):
    solicitud = servicio.exigir_propietario(sesion, solicitud_id, usuario)
    registro = servicio.acuse_de(sesion, solicitud.id)
    archivo = sesion.get(Archivo, registro.archivo_id)
    return FileResponse(ruta_de_archivo(archivo), media_type=archivo.tipo_mime,
                        filename=archivo.nombre_original)
