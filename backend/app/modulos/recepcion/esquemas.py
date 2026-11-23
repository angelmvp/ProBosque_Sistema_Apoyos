from pydantic import BaseModel


class RecepcionEntrada(BaseModel):
    observacion: str = ""
