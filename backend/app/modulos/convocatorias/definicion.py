from app.modulos.convocatorias.rutas_admin import PERMISO, router as router_admin
from app.modulos.convocatorias.rutas_publicas import router as router_publico
from app.nucleo.modulos import DefinicionModulo, OpcionMenu, PermisoDef

DEFINICION = DefinicionModulo(
    clave="convocatorias",
    nombre="M01 Convocatorias y reglas de operación",
    historias=("HU-02", "HU-03"),
    routers=(router_publico, router_admin),
    permisos=(PermisoDef(PERMISO, "Crear, publicar y administrar reglas de operación y convocatorias"),),
    menu=(OpcionMenu("publicaciones", "Publicaciones", "/admin/publicaciones", permiso=PERMISO),),
)
