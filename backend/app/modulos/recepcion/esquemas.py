from pydantic import BaseModel, Field


class DocumentoFaltanteEntrada(BaseModel):
    requisito: str
    observacion: str = ""


class RecepcionEntrada(BaseModel):
    observacion: str = ""
    solicitud_completa: bool = False
    documentos_legibles: bool = False
    corresponden_al_programa: bool = False
    faltantes: list[DocumentoFaltanteEntrada] = Field(default_factory=list)
