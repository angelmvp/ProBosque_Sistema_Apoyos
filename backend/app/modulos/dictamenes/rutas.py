"""Bandeja de dictámenes de la Dirección de Restauración y Fomento Forestal.

En el Sprint 1 solo existe para demostrar la negación de acceso (HU-01-CA-2).
La funcionalidad real llega en sprints posteriores y se agrega aquí.
"""
from fastapi import APIRouter, Depends

from app.servicios.autenticacion.dependencias import requiere_permiso

router = APIRouter(prefix="/api/dictamenes", tags=["Dictámenes"])


@router.get("", summary="Bandeja de dictámenes de la Dirección")
def bandeja(_usuario=Depends(requiere_permiso("dictamenes.ver"))):
    return {"dictamenes": [], "nota": "Funcionalidad pendiente para sprints posteriores."}
