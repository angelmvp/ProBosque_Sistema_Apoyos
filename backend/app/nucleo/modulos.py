"""Contrato que debe cumplir cada módulo del sistema.

Para agregar un módulo nuevo en un sprint futuro:
1. Crear `app/modulos/<nombre>/` con `rutas.py`, `esquemas.py` y `definicion.py`.
2. En `definicion.py` declarar un `DEFINICION = DefinicionModulo(...)`.
3. Agregar el módulo a la lista de `app/modulos/__init__.py`.
No hay que tocar `main.py` ni el núcleo. Los módulos NO se importan entre sí:
solo usan `app.nucleo` y `app.servicios`.
"""
from dataclasses import dataclass, field

from fastapi import APIRouter


@dataclass(frozen=True)
class PermisoDef:
    clave: str
    descripcion: str


@dataclass(frozen=True)
class OpcionMenu:
    clave: str
    etiqueta: str
    ruta: str
    permiso: str | None = None  # None = visible para cualquier persona con sesión


@dataclass(frozen=True)
class DefinicionModulo:
    clave: str
    nombre: str
    historias: tuple[str, ...]
    routers: tuple[APIRouter, ...]
    permisos: tuple[PermisoDef, ...] = field(default_factory=tuple)
    menu: tuple[OpcionMenu, ...] = field(default_factory=tuple)
