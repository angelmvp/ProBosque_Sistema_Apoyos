"""Requisitos documentales aplicables a solicitudes."""
from sqlalchemy import Boolean, ForeignKey, Integer, JSON, Numeric, String, UniqueConstraint
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
    numero: Mapped[int | None] = mapped_column(Integer, nullable=True)
    grupo: Mapped[str] = mapped_column(String(40), default="identidad_representacion")
    programas: Mapped[list] = mapped_column(JSON, default=list)
    tipos_persona: Mapped[list] = mapped_column(JSON, default=list)


class ConceptoSuperficie(Base):
    __tablename__ = "conceptos_superficie"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    clave: Mapped[str] = mapped_column(String(80), unique=True)
    nombre: Mapped[str] = mapped_column(String(255))
    programa_clave: Mapped[str] = mapped_column(String(80))
    orden: Mapped[int] = mapped_column(Integer, default=0)


class SuperficieSolicitud(Base):
    __tablename__ = "superficies_solicitud"
    solicitud_id: Mapped[int] = mapped_column(
        ForeignKey("solicitudes.id", ondelete="CASCADE"), primary_key=True
    )
    concepto_id: Mapped[int] = mapped_column(
        ForeignKey("conceptos_superficie.id"), primary_key=True
    )
    hectareas: Mapped[float] = mapped_column(Numeric(12, 3), nullable=False)


class DocumentoSolicitud(Base):
    __tablename__ = "documentos_solicitud"
    solicitud_id: Mapped[int] = mapped_column(ForeignKey("solicitudes.id", ondelete="CASCADE"), primary_key=True)
    requisito_id: Mapped[int] = mapped_column(ForeignKey("requisitos.id"), primary_key=True)
    archivo_id: Mapped[int | None] = mapped_column(ForeignKey("archivos.id"), nullable=True)
    entregado: Mapped[bool] = mapped_column(Boolean, default=False)
    observacion: Mapped[str] = mapped_column(String(500), default="")
    __table_args__ = (UniqueConstraint("solicitud_id", "requisito_id", name="uq_documento_solicitud_requisito"),)
