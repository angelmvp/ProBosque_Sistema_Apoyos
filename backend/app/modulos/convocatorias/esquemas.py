from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class PublicacionResumen(BaseModel):
    id: int
    titulo: str
    vigencia_inicio: date
    vigencia_fin: date
    estado: str
    publicada_en: datetime | None = None
    url_pdf: str | None = None


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
