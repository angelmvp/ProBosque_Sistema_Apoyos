from app.modulos.solicitudes.rutas import PERMISO, router
from app.nucleo.modulos import BloqueInicio, DefinicionModulo, OpcionMenu, PermisoDef

DEFINICION = DefinicionModulo(
    clave="solicitudes",
    nombre="M02 Solicitudes de apoyo",
    historias=("HU-04", "HU-05", "HU-06"),
    routers=(router,),
    permisos=(PermisoDef(PERMISO, "Crear, completar y enviar solicitudes propias"),),
    menu=(OpcionMenu("mis_solicitudes", "Mis solicitudes", "/solicitudes", permiso=PERMISO),),
    bloques_inicio=(BloqueInicio("mis_solicitudes", "Mis solicitudes",
                                  "Crea, completa y consulta tus solicitudes de apoyo.",
                                  "/solicitudes", permiso=PERMISO),),
)
