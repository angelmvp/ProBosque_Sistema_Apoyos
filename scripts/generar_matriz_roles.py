"""Genera la matriz de permisos y bloques de inicio desde las fuentes reales."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from app.modulos import MODULOS
from app.semillas.roles import ROLES


DESCRIPCIONES_ROLES = {
    "solicitante": "Consulta convocatorias y utiliza los servicios públicos del portal.",
    "delegacion_regional": "Consulta expedientes correspondientes a su delegación regional.",
    "direccion_general": "Administra publicaciones y consulta todos los expedientes.",
    "direccion_restauracion": "Consulta dictámenes y expedientes de todas las delegaciones.",
}


def generar() -> Path:
    filas = []
    for modulo in MODULOS:
        for permiso in modulo.permisos:
            filas.append(("Permiso", modulo.nombre, permiso.clave, permiso.descripcion))
        for bloque in modulo.bloques_inicio:
            filas.append(("Bloque de inicio", modulo.nombre, bloque.clave,
                          f"{bloque.titulo}: {bloque.descripcion}"))

    permisos_por_rol = {
        clave: set(permisos)
        for clave, (_nombre, permisos) in ROLES.items()
    }

    libro = Workbook()
    matriz = libro.active
    matriz.title = "Matriz"
    encabezados = ["Tipo", "Módulo", "Clave", "Descripción"] + [
        nombre for nombre, _permisos in ROLES.values()
    ]
    matriz.append(encabezados)

    for tipo, modulo, clave, descripcion in filas:
        fila = [tipo, modulo, clave, descripcion]
        if tipo == "Permiso":
            permisos_clave = clave
        else:
            bloque = next(
                bloque for mod in MODULOS for bloque in mod.bloques_inicio
                if bloque.clave == clave
            )
            permisos_clave = bloque.permiso
        for rol_clave in ROLES:
            permitido = permisos_clave is None or permisos_clave in permisos_por_rol[rol_clave]
            fila.append("X" if permitido else "")
        matriz.append(fila)

    roles = libro.create_sheet("Roles")
    roles.append(["Clave", "Nombre", "Descripción"])
    for clave, (nombre, _permisos) in ROLES.items():
        roles.append([clave, nombre, DESCRIPCIONES_ROLES[clave]])

    for hoja in (matriz, roles):
        hoja.freeze_panes = "A2"
        hoja.auto_filter.ref = hoja.dimensions
        for celda in hoja[1]:
            celda.font = Font(bold=True)
            celda.fill = PatternFill("solid", fgColor="D9EAF7")
            celda.alignment = Alignment(horizontal="center", vertical="center")
        for columna in range(1, hoja.max_column + 1):
            ancho = max(len(str(hoja.cell(fila, columna).value or "")) for fila in range(1, hoja.max_row + 1))
            hoja.column_dimensions[get_column_letter(columna)].width = min(max(ancho + 2, 12), 55)
        for fila in hoja.iter_rows(min_row=2):
            for celda in fila:
                celda.alignment = Alignment(vertical="top", wrap_text=True)

    destino = ROOT / "docs" / "matriz-de-roles.xlsx"
    destino.parent.mkdir(parents=True, exist_ok=True)
    libro.save(destino)
    return destino


if __name__ == "__main__":
    print(generar())
