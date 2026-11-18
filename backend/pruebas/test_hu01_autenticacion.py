"""HU-01 Autenticación y 4 roles.

HU-01-CA-1: cada rol, al ingresar, ve solo las opciones de menú y la información que le corresponden.
HU-01-CA-2: al intentar entrar a algo sin permiso, el sistema lo niega y lo registra.
"""
from sqlalchemy import select

from app.nucleo import base_datos
from app.servicios.bitacora.modelos import Bitacora

MENU_ESPERADO = {
    "solicitante": {"inicio"},
    "delegacion.toluca": {"inicio", "expedientes"},
    "direccion.general": {"inicio", "publicaciones", "expedientes_todos"},
    "direccion.restauracion": {"inicio", "dictamenes", "expedientes_todos"},
}


def test_ca1_cada_rol_ve_solo_su_menu(como):
    for usuario, esperado in MENU_ESPERADO.items():
        sesion = como(usuario).get("/api/auth/yo").json()
        claves = {o["clave"] for o in sesion["menu"]}
        assert claves == esperado, f"{usuario}: {claves}"


def test_ca1_cada_rol_ve_solo_su_informacion(como):
    from app.nucleo import base_datos as bd
    from app.servicios.catalogo.modelos import Programa, Region
    from app.servicios.expedientes.modelos import Expediente
    s = bd.nueva_sesion()
    programa = s.scalar(select(Programa))
    regiones = {r.clave: r.id for r in s.scalars(select(Region))}
    s.add_all([Expediente(folio="T-1", programa_id=programa.id, region_id=regiones["I"], tramite="x"),
               Expediente(folio="T-2", programa_id=programa.id, region_id=regiones["II"], tramite="x")])
    s.commit(); s.close()
    assert como("solicitante").get("/api/expedientes").status_code == 403
    delegacion = como("delegacion.toluca").get("/api/expedientes").json()
    assert [e["folio"] for e in delegacion] == ["T-1"]          # solo su región
    assert len(como("direccion.general").get("/api/expedientes").json()) == 2


def test_ca2_acceso_denegado_y_registrado(como):
    r = como("solicitante").get("/api/dictamenes")
    assert r.status_code == 403
    s = base_datos.nueva_sesion()
    filas = list(s.scalars(select(Bitacora).where(Bitacora.resultado == "denegado")))
    s.close()
    assert len(filas) == 1 and "dictamenes.ver" in (filas[0].detalle or "") + filas[0].recurso


def test_ca2_el_rol_con_permiso_si_entra(como):
    assert como("direccion.restauracion").get("/api/dictamenes").status_code == 200


def test_ca2_publicaciones_solo_direccion_general(como):
    assert como("solicitante").get("/api/publicaciones").status_code == 403
    assert como("delegacion.toluca").get("/api/publicaciones").status_code == 403
    assert como("direccion.restauracion").get("/api/publicaciones").status_code == 403
    assert como("direccion.general").get("/api/publicaciones").status_code == 200


def test_sin_sesion_responde_401(cliente):
    assert cliente.get("/api/auth/yo").status_code == 401
    assert cliente.get("/api/publicaciones").status_code == 401


def test_credenciales_incorrectas_mensaje_generico_y_bitacora(cliente):
    a = cliente.post("/api/auth/ingresar", json={"correo": "solicitante@probosque.test", "contrasena": "mal"})
    b = cliente.post("/api/auth/ingresar", json={"correo": "nadie@probosque.test", "contrasena": "mal"})
    assert a.status_code == b.status_code == 401
    assert a.json()["mensaje"] == b.json()["mensaje"]


def test_salir_borra_la_sesion(como):
    c = como("solicitante")
    assert c.post("/api/auth/salir").status_code == 204
    c.cookies.clear()
    assert c.get("/api/auth/yo").status_code == 401


def test_inactividad_vence_la_sesion(como):
    from datetime import UTC, datetime, timedelta

    import jwt

    from app.nucleo import seguridad
    from app.nucleo.configuracion import obtener_configuracion
    cfg = obtener_configuracion()
    assert cfg.minutos_inactividad == 30
    token = como("solicitante").cookies.get(cfg.nombre_cookie_sesion)
    assert seguridad.leer_token(token) is not None
    exp = jwt.decode(token, cfg.clave_secreta, algorithms=["HS256"])["exp"]
    restante = exp - datetime.now(UTC).timestamp()
    assert 29 * 60 < restante <= 30 * 60                      # la sesión dura 30 min desde la última actividad
    vencido = jwt.encode({"sub": "1", "exp": datetime.now(UTC) - timedelta(seconds=1)},
                         cfg.clave_secreta, algorithm="HS256")
    assert seguridad.leer_token(vencido) is None
