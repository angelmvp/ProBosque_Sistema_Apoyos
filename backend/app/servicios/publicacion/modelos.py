"""Modelo de SRV-09 Publicación: reglas de operación y convocatorias con vigencia."""
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.nucleo.base_datos import Base
from app.servicios.archivos.modelos import Archivo
from app.servicios.catalogo.modelos import Programa


class Publicacion(Base):
    __tablename__ = "publicaciones"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    programa_id: Mapped[int] = mapped_column(ForeignKey("programas.id"))
    titulo: Mapped[str] = mapped_column(String(200))
    vigencia_inicio: Mapped[date] = mapped_column(Date)
    vigencia_fin: Mapped[date] = mapped_column(Date)
    # None mientras es borrador; al publicar se guarda cuándo y quién.
    publicada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    publicada_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    creada_por_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    creada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)
    programa: Mapped[Programa] = relationship(lazy="joined")
    archivos: Mapped[list["PublicacionArchivo"]] = relationship(
        back_populates="publicacion", lazy="selectin", order_by="PublicacionArchivo.orden"
    )


class PublicacionArchivo(Base):
    __tablename__ = "publicacion_archivos"
    publicacion_id: Mapped[int] = mapped_column(
        ForeignKey("publicaciones.id", ondelete="CASCADE"), primary_key=True
    )
    archivo_id: Mapped[int] = mapped_column(
        ForeignKey("archivos.id", ondelete="RESTRICT"), primary_key=True
    )
    tipo: Mapped[str] = mapped_column(String(30))
    etiqueta: Mapped[str] = mapped_column(String(200))
    orden: Mapped[int] = mapped_column(Integer, default=0)
    publicacion: Mapped[Publicacion] = relationship(back_populates="archivos")
    archivo: Mapped[Archivo] = relationship(lazy="joined")
