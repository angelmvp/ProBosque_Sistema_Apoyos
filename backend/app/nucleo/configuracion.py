"""Configuración central. Todo se lee de variables de entorno (ver `.env.ejemplo`)."""
from functools import lru_cache
from pathlib import Path
from pydantic import AliasChoices
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

RAIZ_BACKEND = Path(__file__).resolve().parents[2]


class Configuracion(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    url_base_datos: str = "postgresql+psycopg://probosque:probosque@localhost:5432/probosque"
    clave_secreta: str = "cambiar-esta-clave-en-produccion"
    minutos_inactividad: int = 30
    nombre_cookie_sesion: str = "sesion_probosque"
    cookie_segura: bool = False
    directorio_archivos: Path = RAIZ_BACKEND / "almacenamiento"
    directorio_formatos: Path = RAIZ_BACKEND.parent / "docs" / "formatos"
    tamano_maximo_pdf_mb: int = 20
    tamano_maximo_documento_mb: int = 10
    tamano_maximo_archivo_mb: int = Field(
        default=20,
        validation_alias=AliasChoices("tamano_maximo_archivo_mb", "TAMANO_MAXIMO_ARCHIVO_MB",
                                      "tamano_maximo_pdf_mb", "TAMANO_MAXIMO_PDF_MB"),
    )
    cargar_datos_demo: bool = True
    entorno: str = "desarrollo"


@lru_cache
def obtener_configuracion() -> Configuracion:
    return Configuracion()
