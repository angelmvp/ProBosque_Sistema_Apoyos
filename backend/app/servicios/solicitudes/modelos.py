"""Entidades persistentes de solicitudes, recepción, folios y acuses."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.nucleo.base_datos import Base


class Solicitud(Base):
    __tablename__ = "solicitudes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    solicitante_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    programa_id: Mapped[int] = mapped_column(ForeignKey("programas.id"))
    municipio_id: Mapped[int] = mapped_column(ForeignKey("municipios.id"))
    region_id: Mapped[int] = mapped_column(ForeignKey("regiones.id"))
    estado: Mapped[str] = mapped_column(String(30), default="borrador")
    datos_501: Mapped[dict] = mapped_column(JSON, default=dict)
    datos_502: Mapped[dict] = mapped_column(JSON, default=dict)
    aviso_privacidad: Mapped[bool] = mapped_column(default=False)
    creada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    actualizada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(),
                                                       onupdate=func.now())
    enviada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    recibida_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    solicitante = relationship("Usuario", lazy="joined")
    programa = relationship("Programa", lazy="joined")
    municipio = relationship("Municipio", lazy="joined")
    region = relationship("Region", lazy="joined")


class Recepcion(Base):
    __tablename__ = "recepciones"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    solicitud_id: Mapped[int] = mapped_column(ForeignKey("solicitudes.id", ondelete="CASCADE"), unique=True)
    receptor_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    observacion: Mapped[str] = mapped_column(Text, default="")
    recibida_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Folio(Base):
    __tablename__ = "folios"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    anio: Mapped[int] = mapped_column(Integer)
    consecutivo: Mapped[int] = mapped_column(Integer)
    solicitud_id: Mapped[int] = mapped_column(ForeignKey("solicitudes.id"), unique=True)
    valor: Mapped[str] = mapped_column(String(40), unique=True)
    __table_args__ = (UniqueConstraint("anio", "consecutivo", name="uq_folio_anio_consecutivo"),)


class Acuse(Base):
    __tablename__ = "acuses"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    solicitud_id: Mapped[int] = mapped_column(ForeignKey("solicitudes.id"), unique=True)
    archivo_id: Mapped[int] = mapped_column(ForeignKey("archivos.id"))
    generado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
