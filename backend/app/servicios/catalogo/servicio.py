"""Consultas del catálogo (SRV-06.1)."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.nucleo.excepciones import NoEncontrado
from app.servicios.catalogo.modelos import Municipio, Programa, Region


def listar_programas(sesion: Session) -> list[Programa]:
    return list(sesion.scalars(select(Programa).order_by(Programa.orden)))


def programa_por_clave(sesion: Session, clave: str) -> Programa:
    programa = sesion.scalar(select(Programa).where(Programa.clave == clave))
    if programa is None:
        raise NoEncontrado("El programa no existe.")
    return programa


def listar_regiones(sesion: Session) -> list[Region]:
    return list(sesion.scalars(select(Region).order_by(Region.id)))


def listar_municipios(sesion: Session, region_id: int | None = None) -> list[Municipio]:
    consulta = select(Municipio).order_by(Municipio.nombre)
    if region_id is not None:
        consulta = consulta.where(Municipio.region_id == region_id)
    return list(sesion.scalars(consulta))


def municipio_por_id(sesion: Session, municipio_id: int) -> Municipio:
    municipio = sesion.get(Municipio, municipio_id)
    if municipio is None:
        raise NoEncontrado("El municipio no existe.")
    return municipio


def region_por_id(sesion: Session, region_id: int) -> Region:
    region = sesion.get(Region, region_id)
    if region is None:
        raise NoEncontrado("La región no existe.")
    return region
