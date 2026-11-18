"""Modelo de SRV-07.2 Bitácora de cambios y accesos."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.nucleo.base_datos import Base


class Bitacora(Base):
    __tablename__ = "bitacora"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    accion: Mapped[str] = mapped_column(String(60))
    recurso: Mapped[str] = mapped_column(String(255))
    resultado: Mapped[str] = mapped_column(String(30))
    detalle: Mapped[str] = mapped_column(Text, default="")
