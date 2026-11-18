"""Preparación de las pruebas: base de datos PostgreSQL real y exclusiva para pruebas.

Usa `URL_BASE_DATOS_PRUEBAS`; si no existe, usa `URL_BASE_DATOS` con el sufijo `_pruebas`
en el nombre de la base (se crea sola si hace falta). Nunca toca la base de desarrollo.
"""
import io
import os
from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from app.semillas.pdf_demo import generar_pdf


def _url_pruebas() -> str:
    explicita = os.environ.get("URL_BASE_DATOS_PRUEBAS")
    if explicita:
        return explicita
    base = make_url(os.environ.get(
        "URL_BASE_DATOS", "postgresql+psycopg://probosque:probosque@localhost:5432/probosque"))
    return base.set(database=f"{base.database}_pruebas").render_as_string(hide_password=False)


URL_PRUEBAS = _url_pruebas()
os.environ["URL_BASE_DATOS"] = URL_PRUEBAS
os.environ["CARGAR_DATOS_DEMO"] = "false"
os.environ.setdefault("CLAVE_SECRETA", "clave-solo-para-pruebas")

from app.main import crear_app  # noqa: E402  (después de fijar el entorno)
from app.nucleo import base_datos  # noqa: E402
from app.nucleo.configuracion import obtener_configuracion  # noqa: E402
from app.modelos import Base  # noqa: E402
from app.semillas import catalogos, roles  # noqa: E402


def _crear_base_si_falta() -> None:
    url = make_url(URL_PRUEBAS)
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as con:
        existe = con.execute(text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": url.database}).scalar()
        if not existe:
            con.execute(text(f'CREATE DATABASE "{url.database}"'))
    admin.dispose()


@pytest.fixture(scope="session", autouse=True)
def _esquema(tmp_path_factory):
    os.environ["DIRECTORIO_ARCHIVOS"] = str(tmp_path_factory.mktemp("archivos"))
    obtener_configuracion.cache_clear()
    _crear_base_si_falta()
    base_datos.reiniciar_motor()
    motor = base_datos.obtener_motor()
    Base.metadata.drop_all(motor)
    Base.metadata.create_all(motor)
    yield
    base_datos.reiniciar_motor()


@pytest.fixture(autouse=True)
def _datos_limpios():
    """Antes de cada prueba: tablas vacías y datos iniciales (catálogos, roles y usuarios)."""
    motor = base_datos.obtener_motor()
    tablas = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
    with motor.begin() as con:
        con.execute(text(f"TRUNCATE {tablas} RESTART IDENTITY CASCADE"))
    sesion = base_datos.nueva_sesion()
    catalogos.cargar(sesion)
    roles.cargar(sesion)
    sesion.commit()
    sesion.close()


@pytest.fixture
def cliente():
    from fastapi.testclient import TestClient
    with TestClient(crear_app()) as c:
        yield c


def _cliente_con_sesion(correo: str):
    from fastapi.testclient import TestClient
    c = TestClient(crear_app())
    c.__enter__()
    r = c.post("/api/auth/ingresar", json={"correo": correo, "contrasena": roles.CONTRASENA_PRUEBA})
    assert r.status_code == 200, r.text
    return c


@pytest.fixture
def como():
    """Devuelve una función: como('direccion.general') -> cliente ya autenticado."""
    abiertos = []

    def _como(usuario: str):
        c = _cliente_con_sesion(f"{usuario}@probosque.test")
        abiertos.append(c)
        return c

    yield _como
    for c in abiertos:
        c.__exit__(None, None, None)


@pytest.fixture
def pdf_valido() -> bytes:
    return generar_pdf("Prueba", ["Contenido de prueba"])


@pytest.fixture
def publicar(como, pdf_valido):
    """Crea una publicación como la Dirección General. Devuelve el JSON de la respuesta."""
    director = como("direccion.general")

    def _publicar(programa="capturando_carbono", titulo="Convocatoria de prueba", desde=-5, hasta=30,
                  accion="publicar"):
        hoy = date.today()
        r = director.post("/api/publicaciones", data={
            "programa": programa, "titulo": titulo, "accion": accion,
            "vigencia_inicio": (hoy + timedelta(days=desde)).isoformat(),
            "vigencia_fin": (hoy + timedelta(days=hasta)).isoformat(),
        }, files={"archivo": ("convocatoria.pdf", io.BytesIO(pdf_valido), "application/pdf")})
        assert r.status_code == 201, r.text
        return r.json()

    return _publicar
