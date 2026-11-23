"""Convierte entidades en esquemas de salida (evita repetir código entre rutas)."""
from pathlib import Path

from app.modulos.convocatorias.esquemas import (
    ArchivoPublicacionSalida, ProgramaPortal, PublicacionAdmin, PublicacionResumen,
)
from app.servicios.publicacion import servicio as publicaciones
from app.servicios.publicacion.modelos import Publicacion
from app.servicios.archivos.almacenamiento import TIPOS_ARCHIVO


def archivos_de(p: Publicacion, *, publico: bool) -> list[ArchivoPublicacionSalida]:
    prefijo = f"/api/publico/publicaciones/{p.id}/archivos" if publico else f"/api/publicaciones/{p.id}/archivos"
    salida = []
    for relacion in p.archivos:
        archivo = relacion.archivo
        salida.append(ArchivoPublicacionSalida(
            id=archivo.id,
            tipo=relacion.tipo,
            nombre_tipo=TIPOS_ARCHIVO.get(relacion.tipo, relacion.tipo),
            etiqueta=relacion.etiqueta,
            nombre_original=archivo.nombre_original,
            extension=Path(archivo.nombre_original).suffix.lower(),
            url=f"{prefijo}/{archivo.id}",
        ))
    return salida


def resumen(p: Publicacion | None, *, publico: bool = True) -> PublicacionResumen | None:
    if p is None:
        return None
    archivos = archivos_de(p, publico=publico)
    convocatoria = next((a for a in archivos if a.tipo == "convocatoria"), None)
    ruta_pdf = convocatoria.url if convocatoria and convocatoria.extension == ".pdf" else None
    return PublicacionResumen(
        id=p.id, titulo=p.titulo, vigencia_inicio=p.vigencia_inicio, vigencia_fin=p.vigencia_fin,
        estado=publicaciones.estado_de(p), publicada_en=p.publicada_en,
        url_pdf=ruta_pdf,
        url_visor=ruta_pdf,
        archivos=archivos,
    )


def para_admin(p: Publicacion) -> PublicacionAdmin:
    base = resumen(p, publico=False)
    return PublicacionAdmin(**base.model_dump(), programa_clave=p.programa.clave,
                            programa_nombre=p.programa.nombre,
                            nombre_archivo=next((a.nombre_original for a in base.archivos), None))


def para_portal(programa, datos: dict) -> ProgramaPortal:
    return ProgramaPortal(
        clave=programa.clave, nombre=programa.nombre, estado=datos["estado"],
        convocatoria_abierta=datos["convocatoria_abierta"],
        publicacion=resumen(datos["publicacion"]), ultima_publicada=resumen(datos["ultima_publicada"]),
    )
