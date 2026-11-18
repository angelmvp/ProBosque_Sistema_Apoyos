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
    archivo_id: Mapped[int | None] = mapped_column(ForeignKey("archivos.id"), nullable=True)
    # None mientras es borrador; al publicar se guarda cuándo y quién.
    publicada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    publicada_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    creada_por_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    creada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)
    programa: Mapped[Programa] = relationship(lazy="joined")
    archivo: Mapped[Archivo | None] = relationship(lazy="joined")
