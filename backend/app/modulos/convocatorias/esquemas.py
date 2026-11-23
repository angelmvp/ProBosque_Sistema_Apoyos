from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class PublicacionResumen(BaseModel):
    id: int
    titulo: str
    vigencia_inicio: date
    vigencia_fin: date
    estado: str
    publicada_en: datetime | None = None
    url_pdf: str | None = None
    url_visor: str | None = None
    archivos: list["ArchivoPublicacionSalida"] = Field(default_factory=list)


class ArchivoPublicacionSalida(BaseModel):
    id: int
    tipo: str
    nombre_tipo: str
    etiqueta: str
    nombre_original: str
    extension: str
    url: str


class ProgramaPortal(BaseModel):
    clave: str
    nombre: str
    estado: str  # vigente | historica | sin_convocatoria
    convocatoria_abierta: bool
    publicacion: PublicacionResumen | None
    ultima_publicada: PublicacionResumen | None


class FormatoSalida(BaseModel):
    clave: str
    nombre: str
    url: str


class MunicipioSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre: str
    region_id: int


class DelegacionSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    clave: str
    nombre: str
    descripcion: str
    domicilio: str | None
    telefono: str | None
    horario: str | None


class RegionSalida(DelegacionSalida):
    pass


class DetalleProgramaPortal(ProgramaPortal):
    formatos: list[FormatoSalida]
    delegacion: DelegacionSalida | None = None
    municipio: MunicipioSalida | None = None


class PublicacionAdmin(PublicacionResumen):
    programa_clave: str
    programa_nombre: str
    nombre_archivo: str | None
