"""Requisitos documentales aplicables a solicitudes."""
from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.nucleo.base_datos import Base


class Requisito(Base):
    __tablename__ = "requisitos"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    clave: Mapped[str] = mapped_column(String(60), unique=True)
    nombre: Mapped[str] = mapped_column(String(255))
    descripcion: Mapped[str] = mapped_column(String(500), default="")
    obligatorio: Mapped[bool] = mapped_column(Boolean, default=True)
    orden: Mapped[int] = mapped_column(Integer, default=0)


class DocumentoSolicitud(Base):
    __tablename__ = "documentos_solicitud"
    solicitud_id: Mapped[int] = mapped_column(ForeignKey("solicitudes.id", ondelete="CASCADE"), primary_key=True)
    requisito_id: Mapped[int] = mapped_column(ForeignKey("requisitos.id"), primary_key=True)
    archivo_id: Mapped[int | None] = mapped_column(ForeignKey("archivos.id"), nullable=True)
    entregado: Mapped[bool] = mapped_column(Boolean, default=False)
    observacion: Mapped[str] = mapped_column(String(500), default="")
    __table_args__ = (UniqueConstraint("solicitud_id", "requisito_id", name="uq_documento_solicitud_requisito"),)
