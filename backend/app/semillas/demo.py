"""Datos de demostración (solo desarrollo). Todo está marcado como ficticio.

- 3 expedientes de ejemplo en dos regiones, para ver el alcance por delegación (HU-01).
- 3 publicaciones de ejemplo (vigente, vigente e histórica) con varios archivos de muestra (HU-02/HU-03).
"""
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.nucleo import tiempo
from app.semillas.pdf_demo import generar_docx_minimo, generar_pdf, generar_xlsx_minimo
from app.servicios.autenticacion.modelos import Usuario
from app.servicios.catalogo.modelos import Programa, Region
from app.servicios.expedientes.modelos import Expediente
from app.servicios.publicacion import servicio as publicaciones
from app.servicios.publicacion.modelos import Publicacion

EXPEDIENTES = [
    ("DEMO-0001", "capturando_carbono", "I", "Revisión documental (ficticio)"),
    ("DEMO-0002", "plantaciones_sustentables", "I", "Visita técnica (ficticio)"),
    ("DEMO-0003", "restauracion_hidrologico_forestal", "II", "Revisión documental (ficticio)"),
]


def cargar(sesion: Session) -> None:
    programas = {p.clave: p for p in sesion.scalars(select(Programa))}
    regiones = {r.clave: r for r in sesion.scalars(select(Region))}
    folios = {e.folio for e in sesion.scalars(select(Expediente))}
    for folio, programa, region, tramite in EXPEDIENTES:
        if folio not in folios:
            sesion.add(Expediente(folio=folio, programa_id=programas[programa].id,
                                  region_id=regiones[region].id, tramite=tramite))
    if sesion.scalar(select(Publicacion.id).limit(1)) is not None:
        return
    direccion = sesion.scalar(select(Usuario).where(Usuario.correo == "direccion.general@probosque.test"))
    hoy = tiempo.fecha_hoy()
    demos = [
        ("capturando_carbono", "Convocatoria Capturando Carbono (ejemplo ficticio)", -30, 90),
        ("plantaciones_sustentables", "Convocatoria Plantaciones Sustentables (ejemplo ficticio)", -10, 120),
        ("servicios_ambientales_hidrologicos", "Convocatoria Servicios Ambientales (ejemplo ficticio, concluida)", -200, -20),
    ]
    for clave, titulo, desde, hasta in demos:
        pdf = generar_pdf(titulo, ["Documento de ejemplo generado por el sistema.",
                                   "Aquí va el PDF real con reglas, requisitos y formatos.",
                                   "Datos ficticios: no tienen validez oficial."])
        publicacion = publicaciones.crear(
            sesion, usuario_id=direccion.id, programa_clave=clave, titulo=titulo,
            vigencia_inicio=hoy + timedelta(days=desde), vigencia_fin=hoy + timedelta(days=hasta),
            nombre_pdf="ejemplo.pdf", contenido_pdf=pdf, publicar=False,
        )
        publicaciones.agregar_archivo(
            sesion, publicacion, usuario_id=direccion.id,
            nombre_original="reglas-de-operacion.docx",
            contenido=generar_docx_minimo("Reglas de operación"),
            tipo="reglas_operacion", etiqueta="Reglas de operación",
        )
        publicaciones.agregar_archivo(
            sesion, publicacion, usuario_id=direccion.id,
            nombre_original="formato-anexo.xlsx",
            contenido=generar_xlsx_minimo("Formato de apoyo"),
            tipo="otro", etiqueta="Formato de apoyo",
        )
        publicaciones.publicar_borrador(sesion, publicacion.id, direccion.id)
