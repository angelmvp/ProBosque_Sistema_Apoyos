"""Punto de entrada de la API. No contiene lógica de negocio: registra módulos y errores."""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.modulos import MODULOS
from app.nucleo.excepciones import ErrorNegocio


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    # Menú y permisos declarados por los módulos; la ruta /api/auth/yo los usa.
    app.state.menu_completo = [opcion for modulo in MODULOS for opcion in modulo.menu]
    app.state.bloques_inicio_completos = [
        bloque for modulo in MODULOS for bloque in modulo.bloques_inicio
    ]
    yield


def crear_app() -> FastAPI:
    app = FastAPI(
        title="PROBOSQUE · Sistema de apoyos forestales",
        description="API del Sprint 1: acceso por rol (HU-01), consulta pública de convocatorias (HU-02) "
                    "y gestión de publicaciones (HU-03).",
        version="0.1.0", lifespan=ciclo_de_vida,
    )
    for modulo in MODULOS:
        for router in modulo.routers:
            app.include_router(router)

    @app.exception_handler(ErrorNegocio)
    async def manejar_error_negocio(_: Request, error: ErrorNegocio):
        return JSONResponse(status_code=error.codigo_http,
                            content={"codigo": error.codigo, "mensaje": error.mensaje,
                                     "campos": error.campos})

    @app.exception_handler(RequestValidationError)
    async def manejar_validacion_peticion(_: Request, error: RequestValidationError):
        campos = [{
            "campo": ".".join(str(parte) for parte in detalle["loc"][1:]),
            "mensaje": detalle["msg"],
        } for detalle in error.errors()]
        return JSONResponse(
            status_code=422,
            content={"codigo": "datos_invalidos", "mensaje": "Revisa los datos enviados.",
                     "campos": campos},
        )

    @app.get("/api/salud", tags=["Sistema"], summary="Comprobación de que la API responde")
    def salud():
        return {"estado": "ok"}

    return app


app = crear_app()
