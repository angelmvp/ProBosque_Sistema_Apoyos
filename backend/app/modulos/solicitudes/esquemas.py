from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class SolicitudCrear(BaseModel):
    programa_id: int
    municipio_id: int


class FormularioSolicitud(BaseModel):
    datos_501: dict | None = None
    datos_502: dict | None = None
    aviso_privacidad: bool | None = None


class SolicitudSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    programa: str
    municipio: str
    delegacion: str
    estado: str
    creada_en: datetime
    enviada_en: datetime | None = None
    recibida_en: datetime | None = None
    folio: str | None = None
    faltantes: list[dict] = Field(default_factory=list)


class DocumentoSalida(BaseModel):
    requisito: str
    nombre: str
    entregado: bool
    observacion: str = ""


class RecepcionEntrada(BaseModel):
    observacion: str = ""
