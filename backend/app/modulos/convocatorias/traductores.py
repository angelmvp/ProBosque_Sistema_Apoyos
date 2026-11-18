"""Convierte entidades en esquemas de salida (evita repetir código entre rutas)."""
from app.modulos.convocatorias.esquemas import ProgramaPortal, PublicacionAdmin, PublicacionResumen
from app.servicios.publicacion import servicio as publicaciones
from app.servicios.publicacion.modelos import Publicacion


def resumen(p: Publicacion | None, *, publico: bool = True) -> PublicacionResumen | None:
    if p is None:
        return None
    ruta = f"/api/publico/publicaciones/{p.id}/pdf" if publico else f"/api/publicaciones/{p.id}/pdf"
    return PublicacionResumen(
        id=p.id, titulo=p.titulo, vigencia_inicio=p.vigencia_inicio, vigencia_fin=p.vigencia_fin,
        estado=publicaciones.estado_de(p), publicada_en=p.publicada_en,
        url_pdf=ruta if p.archivo_id else None,
    )


def para_admin(p: Publicacion) -> PublicacionAdmin:
    base = resumen(p, publico=False)
    return PublicacionAdmin(**base.model_dump(), programa_clave=p.programa.clave,
                            programa_nombre=p.programa.nombre,
                            nombre_archivo=p.archivo.nombre_original if p.archivo else None)


def para_portal(programa, datos: dict) -> ProgramaPortal:
    return ProgramaPortal(
        clave=programa.clave, nombre=programa.nombre, estado=datos["estado"],
        convocatoria_abierta=datos["convocatoria_abierta"],
        publicacion=resumen(datos["publicacion"]), ultima_publicada=resumen(datos["ultima_publicada"]),
    )
