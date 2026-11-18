from pydantic import BaseModel, ConfigDict


class ExpedienteSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    folio: str
    tramite: str
    programa: str
    delegacion: str
