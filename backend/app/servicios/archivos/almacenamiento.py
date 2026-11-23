"""Almacenamiento de archivos. Hoy en disco local; para otro destino (p. ej. S3)
basta con otra clase que cumpla `Almacenamiento` y cambiar `obtener_almacenamiento`."""
import hashlib
import uuid
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Protocol

from sqlalchemy.orm import Session

from app.nucleo.configuracion import obtener_configuracion
from app.nucleo.excepciones import DatosInvalidos, NoEncontrado
from app.servicios.archivos.modelos import Archivo


class Almacenamiento(Protocol):
    def guardar(self, contenido: bytes, extension: str) -> str: ...
    def ruta_absoluta(self, ruta_relativa: str) -> Path: ...


class AlmacenamientoLocal:
    def __init__(self, base: Path):
        self.base = base

    def guardar(self, contenido: bytes, extension: str) -> str:
        nombre = f"{uuid.uuid4().hex}{extension}"
        self.base.mkdir(parents=True, exist_ok=True)
        (self.base / nombre).write_bytes(contenido)
        return nombre

    def ruta_absoluta(self, ruta_relativa: str) -> Path:
        return self.base / ruta_relativa


def obtener_almacenamiento() -> Almacenamiento:
    return AlmacenamientoLocal(obtener_configuracion().directorio_archivos)


def guardar_pdf(sesion: Session, nombre_original: str, contenido: bytes) -> Archivo:
    """Valida que sea un PDF real y de tamaño permitido, lo guarda y registra."""
    limite = obtener_configuracion().tamano_maximo_pdf_mb * 1024 * 1024
    if not contenido:
        raise DatosInvalidos("El archivo está vacío.")
    if len(contenido) > limite:
        raise DatosInvalidos(f"El PDF supera el tamaño máximo de {obtener_configuracion().tamano_maximo_pdf_mb} MB.")
    if not contenido.startswith(b"%PDF"):
        raise DatosInvalidos("El archivo debe ser un PDF.")
    ruta = obtener_almacenamiento().guardar(contenido, ".pdf")
    archivo = Archivo(
        nombre_original=Path(nombre_original).name[:255] or "convocatoria.pdf",
        ruta_relativa=ruta, tipo_mime="application/pdf", tamano_bytes=len(contenido),
        sha256=hashlib.sha256(contenido).hexdigest(),
    )
    sesion.add(archivo)
    sesion.flush()
    return archivo


TIPOS_ARCHIVO = {
    "convocatoria": "Convocatoria",
    "reglas_operacion": "Reglas de operación",
    "formato": "Formato",
    "anexo": "Anexo",
    "otro": "Otro",
}
EXTENSIONES_PERMITIDAS = {".pdf", ".docx", ".xlsx"}


def guardar_archivo(sesion: Session, nombre_original: str, contenido: bytes) -> Archivo:
    """Guarda un PDF, DOCX o XLSX después de validar extensión, firma y tamaño."""
    cfg = obtener_configuracion()
    limite = cfg.tamano_maximo_archivo_mb * 1024 * 1024
    nombre_seguro = Path(nombre_original).name[:255] or "documento"
    extension = Path(nombre_seguro).suffix.lower()
    if not contenido:
        raise DatosInvalidos("El archivo está vacío.")
    if len(contenido) > limite:
        raise DatosInvalidos(f"El archivo supera el tamaño máximo de {cfg.tamano_maximo_archivo_mb} MB.")
    if extension not in EXTENSIONES_PERMITIDAS:
        raise DatosInvalidos("Solo se permiten archivos PDF, DOCX y XLSX.")
    if extension == ".pdf" and not contenido.startswith(b"%PDF"):
        raise DatosInvalidos("El archivo no tiene una firma PDF válida.")
    if extension in {".docx", ".xlsx"}:
        try:
            with zipfile.ZipFile(BytesIO(contenido)) as paquete:
                nombres = set(paquete.namelist())
                requerido = "word/" if extension == ".docx" else "xl/"
                if "[Content_Types].xml" not in nombres or not any(
                    nombre.startswith(requerido) for nombre in nombres
                ):
                    raise DatosInvalidos("El archivo no tiene una firma DOCX/XLSX válida.")
        except (zipfile.BadZipFile, KeyError):
            raise DatosInvalidos("El archivo no tiene una firma DOCX/XLSX válida.")
    ruta = obtener_almacenamiento().guardar(contenido, extension)
    archivo = Archivo(
        nombre_original=nombre_seguro,
        ruta_relativa=ruta,
        tipo_mime={
            ".pdf": "application/pdf",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }[extension],
        tamano_bytes=len(contenido),
        sha256=hashlib.sha256(contenido).hexdigest(),
    )
    sesion.add(archivo)
    sesion.flush()
    return archivo


def ruta_de_archivo(archivo: Archivo) -> Path:
    ruta = obtener_almacenamiento().ruta_absoluta(archivo.ruta_relativa)
    if not ruta.is_file():
        raise NoEncontrado("El archivo no está disponible.")
    return ruta
