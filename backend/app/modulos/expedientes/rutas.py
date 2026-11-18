"""Expedientes visibles según el rol (HU-01-CA-1). HU-04 en adelante los extiende."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.modulos.expedientes.esquemas import ExpedienteSalida
from app.nucleo.base_datos import obtener_sesion
from app.servicios.autenticacion.dependencias import usuario_actual
from app.servicios.autenticacion.modelos import Usuario
from app.servicios.expedientes import servicio

router = APIRouter(prefix="/api/expedientes", tags=["Expedientes"])


@router.get("", response_model=list[ExpedienteSalida], summary="Expedientes que mi rol puede ver")
def listar(usuario: Usuario = Depends(usuario_actual), sesion: Session = Depends(obtener_sesion)):
    return [
        ExpedienteSalida(folio=e.folio, tramite=e.tramite, programa=e.programa.nombre,
                         delegacion=f"{e.region.nombre}")
        for e in servicio.listar_visibles(sesion, usuario)
    ]
