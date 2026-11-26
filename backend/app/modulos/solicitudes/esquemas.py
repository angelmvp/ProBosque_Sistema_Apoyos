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
    programa_clave: str = ""
    municipio: str
    delegacion: str
    estado: str
    creada_en: datetime
    enviada_en: datetime | None = None
    recibida_en: datetime | None = None
    folio: str | None = None
    faltantes: list[dict] = Field(default_factory=list)
    datos_501: dict = Field(default_factory=dict)
    datos_502: dict = Field(default_factory=dict)
    aviso_privacidad: bool = False
    nombre_solicitante: str = ""
    correo_solicitante: str = ""
    acuse_disponible: bool = False
    observacion_recepcion: str = ""


class DocumentoSalida(BaseModel):
    requisito: str
    nombre: str
    entregado: bool
    observacion: str = ""


class RecepcionEntrada(BaseModel):
    observacion: str = ""
    solicitud_completa: bool = False
    documentos_legibles: bool = False
    corresponden_al_programa: bool = False
    faltantes: list[dict[str, str]] = Field(default_factory=list)
