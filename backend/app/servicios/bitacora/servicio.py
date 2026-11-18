"""Registro de eventos relevantes (accesos denegados, inicios de sesión, publicaciones)."""
from sqlalchemy.orm import Session

from app.servicios.bitacora.modelos import Bitacora


def registrar(sesion: Session, *, accion: str, recurso: str, resultado: str,
              detalle: str = "", usuario_id: int | None = None) -> Bitacora:
    evento = Bitacora(accion=accion, recurso=recurso, resultado=resultado,
                      detalle=detalle, usuario_id=usuario_id)
    sesion.add(evento)
    sesion.flush()
    return evento
