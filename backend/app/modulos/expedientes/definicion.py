from app.modulos.expedientes.rutas import router
from app.nucleo.modulos import DefinicionModulo, OpcionMenu, PermisoDef
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
    menu=(OpcionMenu("expedientes", "Expedientes", "/inicio", permiso=VER_DELEGACION),
          OpcionMenu("expedientes_todos", "Todos los expedientes", "/inicio", permiso=VER_TODOS)),
)
