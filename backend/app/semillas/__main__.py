"""Carga datos iniciales: `python -m app.semillas`. Es idempotente (se puede repetir)."""
from app.nucleo.base_datos import nueva_sesion
from app.nucleo.configuracion import obtener_configuracion
from app.semillas import catalogos, demo, roles


def ejecutar() -> None:
    sesion = nueva_sesion()
    try:
        catalogos.cargar(sesion)
        roles.cargar(sesion)
        if obtener_configuracion().cargar_datos_demo:
            demo.cargar(sesion)
        sesion.commit()
        print("Datos iniciales cargados.")
    finally:
        sesion.close()


if __name__ == "__main__":
    ejecutar()
