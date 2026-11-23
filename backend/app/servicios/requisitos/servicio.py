"""Consultas y checklist de requisitos sin dependencia de módulos HTTP."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.servicios.requisitos.modelos import DocumentoSolicitud, Requisito


REQUISITOS_BASE = (
    ("identificacion", "Identificación oficial vigente", "PDF, JPG o PNG"),
    ("curp", "CURP actualizada", "PDF, JPG o PNG"),
    ("registro_502", "FO-PB-502 Registro de información", "Se completa en el formulario"),
    ("propiedad", "Documento de propiedad o posesión", "PDF, JPG o PNG"),
)


def asegurar_catalogo(sesion: Session) -> None:
    existentes = {r.clave for r in sesion.scalars(select(Requisito))}
    for orden, (clave, nombre, descripcion) in enumerate(REQUISITOS_BASE, 1):
        if clave not in existentes:
            sesion.add(Requisito(clave=clave, nombre=nombre, descripcion=descripcion,
                                 obligatorio=True, orden=orden))
    sesion.flush()


def checklist(sesion: Session, solicitud_id: int) -> list[dict]:
    asegurar_catalogo(sesion)
    requisitos = list(sesion.scalars(select(Requisito).order_by(Requisito.orden)))
    entregados = {
        d.requisito_id: d for d in sesion.scalars(
            select(DocumentoSolicitud).where(DocumentoSolicitud.solicitud_id == solicitud_id)
        )
    }
    return [{
        "clave": requisito.clave,
        "nombre": requisito.nombre,
        "descripcion": requisito.descripcion,
        "obligatorio": requisito.obligatorio,
        "entregado": bool(entregados.get(requisito.id) and entregados[requisito.id].entregado),
        "observacion": entregados.get(requisito.id).observacion if entregados.get(requisito.id) else "",
    } for requisito in requisitos]


def faltantes(sesion: Session, solicitud_id: int) -> list[dict]:
    return [item for item in checklist(sesion, solicitud_id)
            if item["obligatorio"] and not item["entregado"]]
