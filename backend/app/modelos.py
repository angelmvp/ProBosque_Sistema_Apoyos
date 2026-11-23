"""Importa todos los modelos para que Alembic y `crear_todo` los conozcan.
Al agregar un servicio con modelos nuevos, importarlo aquí."""
from app.nucleo.base_datos import Base
from app.servicios.archivos.modelos import Archivo  # noqa: F401
from app.servicios.autenticacion.modelos import Permiso, Rol, Usuario, roles_permisos  # noqa: F401
from app.servicios.bitacora.modelos import Bitacora  # noqa: F401
from app.servicios.catalogo.modelos import Municipio, Programa, Region  # noqa: F401
from app.servicios.expedientes.modelos import Expediente  # noqa: F401
from app.servicios.publicacion.modelos import Publicacion, PublicacionArchivo  # noqa: F401
from app.servicios.requisitos.modelos import DocumentoSolicitud, Requisito  # noqa: F401
from app.servicios.solicitudes.modelos import Acuse, Folio, Recepcion, Solicitud  # noqa: F401

__all__ = ["Base"]
