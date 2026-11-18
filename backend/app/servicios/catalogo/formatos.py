"""Formatos oficiales descargables y a qué programas aplican (HU-02).

Los archivos viven en `docs/formatos/`. Qué formato aplica a cada programa está
asignado según el contenido de cada formato; por confirmar con el área.
"""
from dataclasses import dataclass
from pathlib import Path

from app.nucleo.configuracion import obtener_configuracion


@dataclass(frozen=True)
class Formato:
    clave: str
    nombre: str
    archivo: str
    programas: tuple[str, ...]


FORMATOS = (
    Formato("fo-pb-501a", "Solicitud Única FO-PB-501-A", "FO-PB-501A_Solicitud_Unica_2026.docx",
            ("capturando_carbono", "plantaciones_sustentables",
             "restauracion_hidrologico_forestal", "servicios_ambientales_hidrologicos")),
    Formato("fo-pb-502", "Registro de Información FO-PB-502", "FO-PB-502_Registro_de_Informacion_2026.docx",
            ("capturando_carbono", "plantaciones_sustentables", "restauracion_hidrologico_forestal",
             "servicios_ambientales_hidrologicos", "manejo_forestal_sustentable")),
    Formato("sol-guardabosques", "Solicitud Única Guardabosques", "Solicitud_Unica_Guardabosques_2026.docx",
            ("guardabosques",)),
)


def formatos_de_programa(clave_programa: str) -> list[Formato]:
    return [f for f in FORMATOS if clave_programa in f.programas]


def ruta_formato(clave: str) -> Path | None:
    for formato in FORMATOS:
        if formato.clave == clave:
            ruta = obtener_configuracion().directorio_formatos / formato.archivo
            return ruta if ruta.is_file() else None
    return None
