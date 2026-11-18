"""Modelos de SRV-06 Catálogos: programas, regiones (Delegaciones Regionales Forestales) y municipios."""
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.nucleo.base_datos import Base


class Programa(Base):
    __tablename__ = "programas"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    clave: Mapped[str] = mapped_column(String(60), unique=True)
    nombre: Mapped[str] = mapped_column(String(160))
    orden: Mapped[int] = mapped_column(Integer, default=0)


class Region(Base):
    """Región = Delegación Regional Forestal. Datos de contacto por confirmar."""
    __tablename__ = "regiones"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    clave: Mapped[str] = mapped_column(String(10), unique=True)  # I, II, ... IX
    nombre: Mapped[str] = mapped_column(String(120))
    descripcion: Mapped[str] = mapped_column(String(400), default="")
    domicilio: Mapped[str | None] = mapped_column(String(255), nullable=True)
    telefono: Mapped[str | None] = mapped_column(String(60), nullable=True)
    horario: Mapped[str | None] = mapped_column(String(120), nullable=True)
    municipios: Mapped[list["Municipio"]] = relationship(back_populates="region", order_by="Municipio.nombre")


class Municipio(Base):
    __tablename__ = "municipios"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120), unique=True)
    region_id: Mapped[int] = mapped_column(ForeignKey("regiones.id"))
    region: Mapped[Region] = relationship(back_populates="municipios", lazy="joined")
