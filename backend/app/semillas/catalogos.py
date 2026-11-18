"""Datos de catálogo: programas, regiones (Delegaciones Regionales Forestales) y municipios.

Los municipios son los que proporcionó el equipo; la lista no es exhaustiva ("municipios como…").
Domicilio, teléfono y horario de cada delegación: por confirmar.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.servicios.catalogo.modelos import Municipio, Programa, Region

PROGRAMAS = [
    ("capturando_carbono", "Capturando Carbono"),
    ("manejo_forestal_sustentable", "Manejo Forestal Sustentable"),
    ("restauracion_hidrologico_forestal", "Restauración Hidrológico-Forestal"),
    ("servicios_ambientales_hidrologicos", "Servicios Ambientales Hidrológicos"),
    ("plantaciones_sustentables", "Plantaciones Sustentables"),
    ("guardabosques", "Programa Estatal de Guardabosques"),
]

REGIONES = [
    ("I", "Región I Toluca", "Zona central del valle",
     "Toluca, Metepec, Lerma, Ocoyoacac, Otzolotepec, Temoaya, Xonacatlán, Almoloya de Juárez, Calimaya, Tianguistenco, Xalatlaco, Huixquilucan"),
    ("II", "Región II Valle de Bravo", "Poniente de la entidad",
     "Valle de Bravo, Amanalco, Donato Guerra, Villa de Allende, Villa Victoria, Ixtapan del Oro, Santo Tomás, Otzoloapan"),
    ("III", "Región III Tejupilco", "Sur del estado",
     "Tejupilco, Amatepec, Tlatlaya, Luvianos, San Simón de Guerrero"),
    ("IV", "Región IV Coatepec Harinas / Tenancingo", "Zona sur-centro",
     "Coatepec Harinas, Tenancingo, Villa Guerrero, Ixtapan de la Sal, Tonatico, Malinalco, Ocuilan, Zumpahuacán, Texcaltitlán, Sultepec, Zacualpan, Almoloya de Alquisiras"),
    ("V", "Región V Atlacomulco", "Norte de la entidad",
     "Atlacomulco, Acambay, El Oro, Temascalcingo, Jocotitlán, San Felipe del Progreso, San José del Rincón, Ixtlahuaca"),
    ("VI", "Región VI Jilotepec", "Extremo norte y norponiente",
     "Jilotepec, Aculco, Polotitlán, Soyaniquilpan, Timilpan, Chapa de Mota, Morelos, Villa del Carbón"),
    ("VII", "Región VII Naucalpan / Cuautitlán", "Zona metropolitana norponiente",
     "Naucalpan, Nicolás Romero, Atizapán de Zaragoza, Isidro Fabela, Jilotzingo, Tepotzotlán, Huehuetoca"),
    ("VIII", "Región VIII Texcoco", "Oriente y nororiente del valle",
     "Texcoco, Tepetlaoxtoc, Acolman, Otumba, Axapusco, Nopaltepec, Temascalapa"),
    ("IX", "Región IX Amecameca", "Región de los volcanes (zona suroriente)",
     "Amecameca, Tlalmanalco, Chalco, Ixtapaluca, Atlautla, Ecatzingo, Ozumba, Tepetlixpa, Juchitepec, Ayapango, Tenango del Aire, Temamatla"),
]


def cargar(sesion: Session) -> None:
    existentes = {p.clave for p in sesion.scalars(select(Programa))}
    for orden, (clave, nombre) in enumerate(PROGRAMAS, start=1):
        if clave not in existentes:
            sesion.add(Programa(clave=clave, nombre=nombre, orden=orden))
    regiones = {r.clave: r for r in sesion.scalars(select(Region))}
    municipios = {m.nombre for m in sesion.scalars(select(Municipio))}
    for clave, nombre, descripcion, lista in REGIONES:
        region = regiones.get(clave)
        if region is None:
            region = Region(clave=clave, nombre=nombre, descripcion=descripcion)
            sesion.add(region)
            sesion.flush()
        for municipio in (m.strip() for m in lista.split(",")):
            if municipio not in municipios:
                sesion.add(Municipio(nombre=municipio, region_id=region.id))
    sesion.flush()
