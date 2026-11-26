"""Excepciones de negocio. Los servicios las lanzan; `main.py` las convierte en respuestas HTTP."""


class ErrorNegocio(Exception):
    codigo_http = 400
    codigo = "error_negocio"

    def __init__(self, mensaje: str, campos: list[dict[str, str]] | None = None):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.campos = campos or []


class NoEncontrado(ErrorNegocio):
    codigo_http = 404
    codigo = "no_encontrado"


class NoAutenticado(ErrorNegocio):
    codigo_http = 401
    codigo = "no_autenticado"


class AccesoDenegado(ErrorNegocio):
    codigo_http = 403
    codigo = "acceso_denegado"


class DatosInvalidos(ErrorNegocio):
    codigo_http = 422
    codigo = "datos_invalidos"


class Conflicto(ErrorNegocio):
    codigo_http = 409
    codigo = "conflicto"
