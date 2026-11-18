"""Modelo de archivos subidos (base de SRV-03.1 Carga de documentos)."""
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.nucleo.base_datos import Base


class Archivo(Base):
    __tablename__ = "archivos"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre_original: Mapped[str] = mapped_column(String(255))
    ruta_relativa: Mapped[str] = mapped_column(String(400))
    tipo_mime: Mapped[str] = mapped_column(String(100))
    tamano_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
