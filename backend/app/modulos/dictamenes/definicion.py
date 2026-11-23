from app.modulos.dictamenes.rutas import router
from app.nucleo.modulos import BloqueInicio, DefinicionModulo, OpcionMenu, PermisoDef

DEFINICION = DefinicionModulo(
    clave="dictamenes",
    nombre="Dictámenes",
    historias=("HU-01",),
    routers=(router,),
    permisos=(PermisoDef("dictamenes.ver", "Abrir la bandeja de dictámenes de la Dirección"),),
    menu=(OpcionMenu("dictamenes", "Dictámenes", "/dictamenes", permiso="dictamenes.ver"),),
    bloques_inicio=(BloqueInicio("dictamenes", "Dictámenes",
                                 "Consulta la bandeja de dictámenes de la Dirección.",
                                 "/dictamenes", permiso="dictamenes.ver"),),
)
