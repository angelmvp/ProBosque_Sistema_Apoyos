"""Conexión a PostgreSQL y base declarativa de todos los modelos."""
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.nucleo.configuracion import obtener_configuracion


class Base(DeclarativeBase):
    """Todos los modelos heredan de esta clase."""


_motor = None
_fabrica_sesiones = None


def obtener_motor():
    global _motor, _fabrica_sesiones
    if _motor is None:
        _motor = create_engine(obtener_configuracion().url_base_datos, pool_pre_ping=True)
        _fabrica_sesiones = sessionmaker(bind=_motor, expire_on_commit=False)
    return _motor


def reiniciar_motor() -> None:
    """Usado por las pruebas para apuntar a otra base de datos."""
    global _motor, _fabrica_sesiones
    if _motor is not None:
        _motor.dispose()
    _motor = None
    _fabrica_sesiones = None


def nueva_sesion() -> Session:
    obtener_motor()
    return _fabrica_sesiones()


def obtener_sesion() -> Iterator[Session]:
    """Dependencia de FastAPI: una sesión por petición con commit/rollback automático."""
    sesion = nueva_sesion()
    try:
        yield sesion
        sesion.commit()
    except Exception:
        sesion.rollback()
        raise
    finally:
        sesion.close()
