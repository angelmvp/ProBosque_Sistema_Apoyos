"""Registro de módulos. Para sumar un módulo: importar su DEFINICION y agregarla a la lista."""
from app.modulos.acceso.definicion import DEFINICION as ACCESO
from app.modulos.convocatorias.definicion import DEFINICION as CONVOCATORIAS
from app.modulos.dictamenes.definicion import DEFINICION as DICTAMENES
from app.modulos.expedientes.definicion import DEFINICION as EXPEDIENTES

MODULOS = (ACCESO, CONVOCATORIAS, EXPEDIENTES, DICTAMENES)
