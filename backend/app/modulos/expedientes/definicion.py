from app.modulos.expedientes.rutas import router
from app.nucleo.modulos import BloqueInicio, DefinicionModulo, OpcionMenu, PermisoDef
from app.servicios.expedientes.servicio import VER_DELEGACION, VER_TODOS

DEFINICION = DefinicionModulo(
    clave="expedientes",
    nombre="Expedientes",
    historias=("HU-01",),
    routers=(router,),
    permisos=(
        PermisoDef(VER_DELEGACION, "Ver los expedientes de la propia delegación"),
        PermisoDef(VER_TODOS, "Ver los expedientes de todas las delegaciones"),
    ),
    menu=(OpcionMenu("expedientes", "Expedientes", "/expedientes", permiso=VER_DELEGACION),
          OpcionMenu("expedientes_todos", "Todos los expedientes", "/expedientes", permiso=VER_TODOS)),
    bloques_inicio=(
        BloqueInicio("expedientes_delegacion", "Expedientes de mi delegación",
                     "Consulta los expedientes que corresponden a tu delegación.",
                     "/expedientes", permiso=VER_DELEGACION),
        BloqueInicio("expedientes_todos", "Todos los expedientes",
                     "Consulta los expedientes de todas las delegaciones.",
                     "/expedientes", permiso=VER_TODOS),
    ),
)
