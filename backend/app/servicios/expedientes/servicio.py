"""Consulta de expedientes con alcance por rol (HU-01-CA-1)."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.servicios.autenticacion.modelos import Usuario
from app.servicios.autenticacion.servicio import exigir_permiso, permisos_de
from app.servicios.expedientes.modelos import Expediente

VER_TODOS = "expedientes.ver_todos"
VER_DELEGACION = "expedientes.ver_delegacion"


def listar_visibles(sesion: Session, usuario: Usuario) -> list[Expediente]:
    """Dirección ve todos; una delegación solo los de su región; el resto recibe 403."""
    permisos = permisos_de(usuario)
    consulta = select(Expediente).order_by(Expediente.id)
    if VER_TODOS in permisos:
        return list(sesion.scalars(consulta))
    exigir_permiso(sesion, usuario, VER_DELEGACION, recurso="/api/expedientes")
    if usuario.region_id is None:
        return []
    return list(sesion.scalars(consulta.where(Expediente.region_id == usuario.region_id)))
