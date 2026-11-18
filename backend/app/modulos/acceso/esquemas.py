from pydantic import BaseModel, Field


class SolicitudIngreso(BaseModel):
    correo: str = Field(min_length=3, max_length=255)
    contrasena: str = Field(min_length=1, max_length=200)


class RolSalida(BaseModel):
    clave: str
    nombre: str


class RegionSalida(BaseModel):
    id: int
    clave: str
    nombre: str


class OpcionMenuSalida(BaseModel):
    clave: str
    etiqueta: str
    ruta: str


class SesionSalida(BaseModel):
    nombre: str
    correo: str
    rol: RolSalida
    region: RegionSalida | None
    permisos: list[str]
    menu: list[OpcionMenuSalida]
    minutos_inactividad: int
