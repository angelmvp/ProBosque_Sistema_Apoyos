from app.modulos.recepcion.rutas import PERMISO, router
from app.nucleo.modulos import BloqueInicio, DefinicionModulo, OpcionMenu, PermisoDef

DEFINICION = DefinicionModulo(
    clave="recepcion",
    nombre="M03 Recepción de solicitudes",
    historias=("HU-07",),
    routers=(router,),
    permisos=(PermisoDef(PERMISO, "Recibir solicitudes de la delegación regional"),),
    menu=(OpcionMenu("recepcion", "Recepción", "/recepcion", permiso=PERMISO),),
    bloques_inicio=(BloqueInicio("recepcion", "Solicitudes recibidas",
                                  "Revisa y recibe solicitudes de tu delegación.",
                                  "/recepcion", permiso=PERMISO),),
)
