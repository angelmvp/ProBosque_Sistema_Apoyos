"""Estructura mínima de expedientes (base de SRV-03). HU-04 en adelante la extenderá."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.nucleo.base_datos import Base
from app.servicios.catalogo.modelos import Programa, Region


class Expediente(Base):
    __tablename__ = "expedientes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    folio: Mapped[str] = mapped_column(String(40), unique=True)
    programa_id: Mapped[int] = mapped_column(ForeignKey("programas.id"))
    region_id: Mapped[int] = mapped_column(ForeignKey("regiones.id"))
    tramite: Mapped[str] = mapped_column(String(160))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    programa: Mapped[Programa] = relationship(lazy="joined")
    region: Mapped[Region] = relationship(lazy="joined")
