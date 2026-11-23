"""Roles, permisos y usuarios de prueba (Sprint 1: solo estos 4 roles).

IMPORTANTE: las contraseñas de prueba son SOLO para desarrollo local.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modulos import MODULOS
from app.nucleo.seguridad import generar_hash
from app.servicios.autenticacion.modelos import Permiso, Rol, Usuario
from app.servicios.catalogo.modelos import Region

CONTRASENA_PRUEBA = "Probosque2026!"

# clave del rol -> (nombre, permisos)
ROLES = {
    "solicitante": ("Persona solicitante", ["convocatorias.consultar"]),
    "delegacion_regional": ("Delegación Regional Forestal", ["expedientes.ver_delegacion"]),
    "direccion_general": ("Dirección General de PROBOSQUE",
                          ["publicaciones.gestionar", "expedientes.ver_todos"]),
    "direccion_restauracion": ("Dirección de Restauración y Fomento Forestal",
                               ["dictamenes.ver", "expedientes.ver_todos"]),
}

USUARIOS = [
    ("solicitante@probosque.test", "Sofía", "Solicitante", "Prueba", "solicitante", None),
    ("delegacion.toluca@probosque.test", "Daniel", "Delegación", "Toluca", "delegacion_regional", "I"),
    ("direccion.general@probosque.test", "Gabriela", "Dirección", "General", "direccion_general", None),
    ("direccion.restauracion@probosque.test", "Raúl", "Restauración", "Forestal", "direccion_restauracion", None),
]


def cargar(sesion: Session) -> None:
    permisos = {p.clave: p for p in sesion.scalars(select(Permiso))}
    for modulo in MODULOS:
        for definicion in modulo.permisos:
            if definicion.clave not in permisos:
                permisos[definicion.clave] = Permiso(clave=definicion.clave, descripcion=definicion.descripcion)
                sesion.add(permisos[definicion.clave])
    sesion.flush()
    roles = {r.clave: r for r in sesion.scalars(select(Rol))}
    for clave, (nombre, claves_permisos) in ROLES.items():
        rol = roles.get(clave) or Rol(clave=clave, nombre=nombre)
        sesion.add(rol)
        rol.nombre = nombre
        rol.permisos = [permisos[c] for c in claves_permisos]
        roles[clave] = rol
    sesion.flush()
    regiones = {r.clave: r for r in sesion.scalars(select(Region))}
    existentes = {u.correo for u in sesion.scalars(select(Usuario))}
    for correo, nombre, apellido_paterno, apellido_materno, clave_rol, clave_region in USUARIOS:
        if correo not in existentes:
            sesion.add(Usuario(correo=correo, nombre=nombre, hash_contrasena=generar_hash(CONTRASENA_PRUEBA),
                               apellido_paterno=apellido_paterno, apellido_materno=apellido_materno,
                               rol_id=roles[clave_rol].id,
                               region_id=regiones[clave_region].id if clave_region else None))
    sesion.flush()
