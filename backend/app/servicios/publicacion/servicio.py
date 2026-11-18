"""Lógica de SRV-09: crear, publicar y consultar publicaciones.

Reglas del backlog:
- Una publicación se guarda como borrador o se publica (HU-03-CA-1).
- Una publicación NO se despublica. Al vencer su vigencia pasa sola a «histórica»,
  sigue publicada y ya no permite iniciar solicitudes nuevas (HU-03-CA-2).
"""
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.nucleo import tiempo
from app.nucleo.excepciones import Conflicto, DatosInvalidos, NoEncontrado
from app.servicios.archivos import almacenamiento
from app.servicios.bitacora import servicio as bitacora
from app.servicios.catalogo import servicio as catalogo
from app.servicios.publicacion.modelos import Publicacion

BORRADOR = "borrador"
PROGRAMADA = "programada"
VIGENTE = "vigente"
HISTORICA = "historica"


def estado_de(publicacion: Publicacion, hoy: date | None = None) -> str:
    """Estado calculado; no se guarda, así que cambia solo al vencer la vigencia."""
    if publicacion.publicada_en is None:
        return BORRADOR
    hoy = hoy or tiempo.fecha_hoy()
    if hoy < publicacion.vigencia_inicio:
        return PROGRAMADA
    if hoy > publicacion.vigencia_fin:
        return HISTORICA
    return VIGENTE


def _validar(titulo: str, inicio: date, fin: date) -> str:
    titulo = (titulo or "").strip()
    if not titulo:
        raise DatosInvalidos("El título es obligatorio.")
    if len(titulo) > 200:
        raise DatosInvalidos("El título no debe pasar de 200 caracteres.")
    if fin < inicio:
        raise DatosInvalidos("La vigencia termina antes de empezar.")
    return titulo


def obtener(sesion: Session, publicacion_id: int) -> Publicacion:
    publicacion = sesion.get(Publicacion, publicacion_id)
    if publicacion is None:
        raise NoEncontrado("La publicación no existe.")
    return publicacion


def _exigir_borrador(publicacion: Publicacion) -> None:
    if publicacion.publicada_en is not None:
        raise Conflicto("La publicación ya está publicada y no se puede modificar ni despublicar.")


def _publicar(sesion: Session, publicacion: Publicacion, usuario_id: int) -> None:
    if publicacion.archivo_id is None:
        raise DatosInvalidos("Para publicar hay que adjuntar el PDF de la convocatoria.")
    publicacion.publicada_en = datetime.now(UTC)
    publicacion.publicada_por_id = usuario_id
    bitacora.registrar(sesion, accion="publicar", recurso=f"publicacion/{publicacion.id}",
                       resultado="exitoso", usuario_id=usuario_id,
                       detalle=f"programa={publicacion.programa.clave}")


def crear(sesion: Session, *, usuario_id: int, programa_clave: str, titulo: str,
          vigencia_inicio: date, vigencia_fin: date, nombre_pdf: str | None,
          contenido_pdf: bytes | None, publicar: bool) -> Publicacion:
    titulo = _validar(titulo, vigencia_inicio, vigencia_fin)
    programa = catalogo.programa_por_clave(sesion, programa_clave)
    archivo = almacenamiento.guardar_pdf(sesion, nombre_pdf or "convocatoria.pdf", contenido_pdf) \
        if contenido_pdf else None
    publicacion = Publicacion(programa_id=programa.id, titulo=titulo, vigencia_inicio=vigencia_inicio,
                              vigencia_fin=vigencia_fin, archivo_id=archivo.id if archivo else None,
                              creada_por_id=usuario_id)
    sesion.add(publicacion)
    sesion.flush()
    sesion.refresh(publicacion)
    if publicar:
        _publicar(sesion, publicacion, usuario_id)
    return publicacion


def actualizar_borrador(sesion: Session, publicacion_id: int, *, usuario_id: int, programa_clave: str,
                        titulo: str, vigencia_inicio: date, vigencia_fin: date,
                        nombre_pdf: str | None, contenido_pdf: bytes | None,
                        publicar: bool) -> Publicacion:
    publicacion = obtener(sesion, publicacion_id)
    _exigir_borrador(publicacion)
    publicacion.titulo = _validar(titulo, vigencia_inicio, vigencia_fin)
    publicacion.programa_id = catalogo.programa_por_clave(sesion, programa_clave).id
    publicacion.vigencia_inicio, publicacion.vigencia_fin = vigencia_inicio, vigencia_fin
    if contenido_pdf:
        publicacion.archivo_id = almacenamiento.guardar_pdf(
            sesion, nombre_pdf or "convocatoria.pdf", contenido_pdf).id
    sesion.flush()
    sesion.refresh(publicacion)
    if publicar:
        _publicar(sesion, publicacion, usuario_id)
    return publicacion


def publicar_borrador(sesion: Session, publicacion_id: int, usuario_id: int) -> Publicacion:
    publicacion = obtener(sesion, publicacion_id)
    _exigir_borrador(publicacion)
    _publicar(sesion, publicacion, usuario_id)
    return publicacion


def eliminar_borrador(sesion: Session, publicacion_id: int) -> None:
    publicacion = obtener(sesion, publicacion_id)
    _exigir_borrador(publicacion)
    sesion.delete(publicacion)


def listar(sesion: Session, programa_clave: str | None = None) -> list[Publicacion]:
    consulta = select(Publicacion).order_by(Publicacion.vigencia_inicio.desc(), Publicacion.id.desc())
    if programa_clave:
        consulta = consulta.where(Publicacion.programa.has(clave=programa_clave))
    return list(sesion.scalars(consulta))


# ---------------- Consulta pública (HU-02) ----------------

def publicadas_de_programa(sesion: Session, programa_id: int) -> list[Publicacion]:
    return list(sesion.scalars(
        select(Publicacion)
        .where(Publicacion.programa_id == programa_id, Publicacion.publicada_en.is_not(None))
        .order_by(Publicacion.vigencia_inicio.desc(), Publicacion.id.desc())))


def resumen_de_programa(sesion: Session, programa_id: int) -> dict:
    """Qué muestra el portal para un programa (HU-02-CA-1 y HU-02-CA-2)."""
    publicadas = publicadas_de_programa(sesion, programa_id)
    vigentes = [p for p in publicadas if estado_de(p) == VIGENTE]
    ultima = max(publicadas, key=lambda p: p.publicada_en, default=None)
    if vigentes:
        estado, principal = VIGENTE, vigentes[0]
    elif any(estado_de(p) == HISTORICA for p in publicadas):
        estado = HISTORICA
        principal = next(p for p in publicadas if estado_de(p) == HISTORICA)
    else:
        estado, principal = "sin_convocatoria", None
    return {"estado": estado, "convocatoria_abierta": estado == VIGENTE,
            "publicacion": principal, "ultima_publicada": ultima}


def publicacion_publica(sesion: Session, publicacion_id: int) -> Publicacion:
    """Solo se exponen al público las publicaciones ya publicadas."""
    publicacion = sesion.get(Publicacion, publicacion_id)
    if publicacion is None or publicacion.publicada_en is None:
        raise NoEncontrado("La publicación no existe.")
    return publicacion
