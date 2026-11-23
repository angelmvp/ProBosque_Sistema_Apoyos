from app.modulos.acceso.rutas import router
from app.nucleo.modulos import BloqueInicio, DefinicionModulo, OpcionMenu

DEFINICION = DefinicionModulo(
    clave="acceso",
    nombre="Acceso al sistema",
    historias=("HU-01",),
    routers=(router,),
    menu=(OpcionMenu("inicio", "Inicio", "/inicio"),),
    bloques_inicio=(BloqueInicio("perfil", "Mi perfil", "Consulta tus datos personales y tu rol.", "/perfil"),),
)
