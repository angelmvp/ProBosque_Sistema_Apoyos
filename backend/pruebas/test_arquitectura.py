"""Pruebas de arquitectura: protegen la estructura base para los siguientes sprints.

- Los módulos NO se importan entre sí (solo usan `app.nucleo` y `app.servicios`).
- Los servicios compartidos NO dependen de los módulos.
- Los permisos y las claves de módulo no se repiten.
"""
import ast
from pathlib import Path

from app.modulos import MODULOS

RAIZ = Path(__file__).resolve().parents[1] / "app"


def _importaciones(carpeta: Path):
    for archivo in carpeta.rglob("*.py"):
        for nodo in ast.walk(ast.parse(archivo.read_text(encoding="utf-8"))):
            if isinstance(nodo, ast.ImportFrom) and nodo.module:
                yield archivo, nodo.module
            elif isinstance(nodo, ast.Import):
                for alias in nodo.names:
                    yield archivo, alias.name


def test_los_modulos_no_se_importan_entre_si():
    for carpeta in (RAIZ / "modulos").iterdir():
        if not carpeta.is_dir() or carpeta.name.startswith("__"):
            continue
        for archivo, modulo in _importaciones(carpeta):
            if modulo.startswith("app.modulos."):
                propio = f"app.modulos.{carpeta.name}"
                assert modulo == propio or modulo.startswith(propio + "."), f"{archivo}: importa {modulo}"


def test_los_servicios_no_dependen_de_los_modulos():
    for archivo, modulo in _importaciones(RAIZ / "servicios"):
        assert not modulo.startswith("app.modulos"), f"{archivo}: importa {modulo}"


def test_el_nucleo_no_depende_de_nada_de_negocio():
    for archivo, modulo in _importaciones(RAIZ / "nucleo"):
        assert not modulo.startswith(("app.modulos", "app.servicios")), f"{archivo}: importa {modulo}"


def test_claves_unicas():
    claves = [m.clave for m in MODULOS]
    assert len(claves) == len(set(claves))
    permisos = [p.clave for m in MODULOS for p in m.permisos]
    assert len(permisos) == len(set(permisos))
