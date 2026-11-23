from app.modulos.convocatorias.rutas_admin import PERMISO, router as router_admin
from app.modulos.convocatorias.rutas_publicas import router as router_publico
from app.nucleo.modulos import BloqueInicio, DefinicionModulo, OpcionMenu, PermisoDef

PERMISO_CONSULTAR = "convocatorias.consultar"

DEFINICION = DefinicionModulo(
    clave="convocatorias",
    nombre="M01 Convocatorias y reglas de operación",
    historias=("HU-02", "HU-03"),
    routers=(router_publico, router_admin),
    permisos=(
        PermisoDef(PERMISO, "Crear, publicar y administrar reglas de operación y convocatorias"),
        PermisoDef(PERMISO_CONSULTAR, "Consultar convocatorias del portal público"),
    ),
    menu=(OpcionMenu("publicaciones", "Publicaciones", "/admin/publicaciones", permiso=PERMISO),),
    bloques_inicio=(
        BloqueInicio("publicaciones", "Publicaciones", "Crea y administra convocatorias.",
                     "/admin/publicaciones", permiso=PERMISO),
        BloqueInicio("consultar_convocatorias", "Consultar convocatorias",
                     "Revisa programas, requisitos y documentos disponibles.",
                     "/", permiso=PERMISO_CONSULTAR),
    ),
)
