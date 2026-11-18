"""Contraseñas (argon2) y tokens de sesión (JWT con vencimiento por inactividad)."""
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.nucleo.configuracion import obtener_configuracion

_hasher = PasswordHasher()


def generar_hash(contrasena: str) -> str:
    return _hasher.hash(contrasena)


def verificar_contrasena(contrasena: str, hash_guardado: str) -> bool:
    try:
        return _hasher.verify(hash_guardado, contrasena)
    except VerifyMismatchError:
        return False


def crear_token(usuario_id: int) -> str:
    cfg = obtener_configuracion()
    vence = datetime.now(UTC) + timedelta(minutes=cfg.minutos_inactividad)
    return jwt.encode({"sub": str(usuario_id), "exp": vence}, cfg.clave_secreta, algorithm="HS256")


def leer_token(token: str) -> int | None:
    """Devuelve el id de usuario o None si el token es inválido o ya venció."""
    try:
        datos = jwt.decode(token, obtener_configuracion().clave_secreta, algorithms=["HS256"])
        return int(datos["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None
