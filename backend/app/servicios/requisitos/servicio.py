"""Catálogos y checklist documental de solicitudes."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.servicios.requisitos.modelos import (
    ConceptoSuperficie, DocumentoSolicitud, Requisito, SuperficieSolicitud,
)


REQUISITOS = (
    (1, "identificacion", "Identificación oficial vigente con fotografía",
     "Si no trae domicilio: comprobante de domicilio con antigüedad máxima de 3 meses",
     "identidad_representacion", (), (), True),
    (2, "curp", "CURP actualizada", "", "identidad_representacion", (), (), True),
    (3, "registro_502", "FO-PB-502 Registro de información",
     "Se completa en línea en el paso 2", "identidad_representacion", (), (), True),
    (4, "propiedad", "Documento de propiedad o posesión", "",
     "propiedad_modalidad", (), (), True),
    (5, "acta_incorporacion", "Ejidos y comunidades: acta de asamblea de incorporación",
     "Inscrita o presentada para trámite ante el RAN", "propiedad_modalidad", (),
     ("nucleo_agrario",), True),
    (6, "acta_representacion", "Ejidos y comunidades: acta de elección de órganos de representación",
     "O credenciales vigentes del RAN", "identidad_representacion", (),
     ("nucleo_agrario",), True),
    (7, "constitucion", "Personas jurídicas colectivas: constitución protocolizada",
     "Con facultades de administración", "identidad_representacion", (),
     ("sociedad",), True),
    (8, "representacion_legal", "Representante legal: documento de representación",
     "Con facultades de administración y/o dominio, cuando aplique",
     "identidad_representacion", (), (), False),
    (9, "proyecto_rhf", "Proyecto Técnico de Restauración Forestal Integral",
     "Restauración Hidrológico-Forestal", "programa",
     ("restauracion_hidrologico_forestal",), (), True),
    (10, "registro_plantacion", "Registro de plantación o constancia de trámite",
     "Capturando Carbono o mantenimiento de plantaciones navideñas",
     "programa", ("capturando_carbono",), (), True),
    (11, "certificado_manejo", "Certificado del Manejo Forestal",
     "Pago por Servicios Ambientales Hidrológicos (PSAHEM)",
     "programa", ("servicios_ambientales_hidrologicos",), (), True),
)

CONCEPTOS = (
    ("cc_maderable", "Plantación forestal comercial maderable", "capturando_carbono"),
    ("cc_navidena", "Plantación forestal comercial navideña", "capturando_carbono"),
    ("cc_reforestacion", "Reforestación", "capturando_carbono"),
    ("rhf_modalidad_uno", "Restauración Forestal Integral, modalidad uno",
     "restauracion_hidrologico_forestal"),
    ("rhf_modalidad_dos", "Restauración Forestal Integral, modalidad dos",
     "restauracion_hidrologico_forestal"),
    ("rhf_bosques_agua", "Bosques de Agua", "restauracion_hidrologico_forestal"),
    ("rhf_preservacion_2023", "Preservación de reforestaciones establecidas 2023",
     "restauracion_hidrologico_forestal"),
    ("rhf_preservacion_2024", "Preservación de reforestaciones establecidas 2024",
     "restauracion_hidrologico_forestal"),
    ("rhf_preservacion_2025", "Preservación de reforestaciones establecidas 2025",
     "restauracion_hidrologico_forestal"),
    ("ps_maderable", "Plantación forestal comercial maderable", "plantaciones_sustentables"),
    ("ps_navidena", "Plantación forestal comercial navideña", "plantaciones_sustentables"),
    ("ps_agave", "Agave", "plantaciones_sustentables"),
    ("ps_celulosico", "Celulósico", "plantaciones_sustentables"),
    ("ps_dendroenergeticos", "Dendroenergéticos", "plantaciones_sustentables"),
    ("ps_follaje", "Follaje", "plantaciones_sustentables"),
    ("ps_biocombustible", "Biocombustible", "plantaciones_sustentables"),
    ("ps_agroforestal", "Agroforestal", "plantaciones_sustentables"),
    ("ps_otros", "Otros", "plantaciones_sustentables"),
    ("ps_mantenimiento_2023", "Mantenimiento de plantaciones forestales comerciales 2023",
     "plantaciones_sustentables"),
    ("ps_mantenimiento_2024", "Mantenimiento de plantaciones forestales comerciales 2024",
     "plantaciones_sustentables"),
    ("ps_mantenimiento_2025", "Mantenimiento de plantaciones forestales comerciales 2025",
     "plantaciones_sustentables"),
    ("ps_mantenimiento_navidena", "Mantenimiento de plantaciones navideñas",
     "plantaciones_sustentables"),
    ("psahem_superficie", "Superficie a incorporar", "servicios_ambientales_hidrologicos"),
    ("psahem_concurrente", "Superficie con fondos concurrentes PSA-CONAFOR",
     "servicios_ambientales_hidrologicos"),
)


def asegurar_catalogo(sesion: Session) -> None:
    existentes = {r.clave: r for r in sesion.scalars(select(Requisito))}
    for orden, (numero, clave, nombre, descripcion, grupo, programas, tipos, obligatorio) in enumerate(
        REQUISITOS, 1
    ):
        requisito = existentes.get(clave)
        if requisito is None:
            requisito = Requisito(clave=clave)
            sesion.add(requisito)
        requisito.numero = numero
        requisito.nombre = nombre
        requisito.descripcion = descripcion
        requisito.grupo = grupo
        requisito.programas = list(programas)
        requisito.tipos_persona = list(tipos)
        requisito.obligatorio = obligatorio
        requisito.orden = orden

    conceptos_existentes = {
        concepto.clave: concepto for concepto in sesion.scalars(select(ConceptoSuperficie))
    }
    for orden, (clave, nombre, programa) in enumerate(CONCEPTOS, 1):
        concepto = conceptos_existentes.get(clave)
        if concepto is None:
            concepto = ConceptoSuperficie(clave=clave)
            sesion.add(concepto)
        concepto.nombre = nombre
        concepto.programa_clave = programa
        concepto.orden = orden
    sesion.flush()


def checklist(sesion: Session, solicitud_id: int, programa_clave: str = "",
              tipo_persona: str = "", datos_501: dict | None = None) -> list[dict]:
    asegurar_catalogo(sesion)
    requisitos = list(sesion.scalars(select(Requisito).order_by(Requisito.orden)))
    entregados = {
        d.requisito_id: d for d in sesion.scalars(
            select(DocumentoSolicitud).where(DocumentoSolicitud.solicitud_id == solicitud_id)
        )
    }
    archivo_por_id = {}
    if entregados:
        from app.servicios.archivos.modelos import Archivo
        archivo_por_id = {
            archivo.id: archivo for archivo in sesion.scalars(
                select(Archivo).where(Archivo.id.in_(
                    [d.archivo_id for d in entregados.values() if d.archivo_id]
                ))
            )
        }
    superficies = (datos_501 or {}).get("superficies", {})
    if not isinstance(superficies, dict):
        superficies = {}
    try:
        mantenimiento_navidena = float(superficies.get("ps_mantenimiento_navidena", 0) or 0) > 0
    except (TypeError, ValueError):
        mantenimiento_navidena = False
    return [{
        "clave": requisito.clave,
        "numero": requisito.numero,
        "nombre": requisito.nombre,
        "descripcion": requisito.descripcion,
        "grupo": requisito.grupo,
        "obligatorio": requisito.obligatorio,
        "aplica": (
            (not requisito.programas or programa_clave in requisito.programas)
            and (not requisito.tipos_persona or tipo_persona in requisito.tipos_persona)
            and not (
                requisito.clave == "registro_plantacion"
                and programa_clave == "plantaciones_sustentables"
                and not mantenimiento_navidena
            )
        ),
        "entregado": bool(entregados.get(requisito.id) and entregados[requisito.id].entregado),
        "observacion": entregados.get(requisito.id).observacion if entregados.get(requisito.id) else "",
        "archivo_id": entregados.get(requisito.id).archivo_id if entregados.get(requisito.id) else None,
        "archivo_nombre": (
            archivo_por_id[entregados[requisito.id].archivo_id].nombre_original
            if entregados.get(requisito.id) and entregados[requisito.id].archivo_id in archivo_por_id
            else None
        ),
        "archivo_tamano": (
            archivo_por_id[entregados[requisito.id].archivo_id].tamano_bytes
            if entregados.get(requisito.id) and entregados[requisito.id].archivo_id in archivo_por_id
            else None
        ),
        "url_archivo": (
            f"/api/solicitudes/{solicitud_id}/documentos/{requisito.clave}/archivo"
            if entregados.get(requisito.id) and entregados[requisito.id].archivo_id
            else None
        ),
    } for requisito in requisitos]


def faltantes(sesion: Session, solicitud_id: int, programa_clave: str = "",
              tipo_persona: str = "", datos_501: dict | None = None) -> list[dict]:
    return [item for item in checklist(sesion, solicitud_id, programa_clave, tipo_persona, datos_501)
            if item["aplica"] and item["obligatorio"] and not item["entregado"]]


def guardar_superficies(sesion: Session, solicitud_id: int, datos_501: dict,
                        programa_clave: str) -> None:
    from app.nucleo.excepciones import DatosInvalidos

    superficies = datos_501.get("superficies", {})
    if not isinstance(superficies, dict):
        raise DatosInvalidos(
            "Las superficies deben enviarse como conceptos y hectáreas.",
            [{"campo": "datos_501.superficies", "mensaje": "Formato de superficies no válido."}],
        )
    conceptos = {c.clave: c for c in sesion.scalars(select(ConceptoSuperficie))}
    permitidos = {clave for clave, concepto in conceptos.items()
                  if concepto.programa_clave == programa_clave}
    desconocidos = set(superficies) - permitidos
    if desconocidos:
        clave = sorted(desconocidos)[0]
        raise DatosInvalidos(
            "El concepto de superficie no corresponde al programa seleccionado.",
            [{"campo": f"datos_501.superficies.{clave}",
              "mensaje": "Concepto no válido para el programa."}],
        )
    actuales = {
        s.concepto_id: s for s in sesion.scalars(
            select(SuperficieSolicitud).where(SuperficieSolicitud.solicitud_id == solicitud_id)
        )
    }
    for clave, concepto in conceptos.items():
        if clave not in permitidos:
            continue
        valor = superficies.get(clave)
        registro = actuales.get(concepto.id)
        if valor in (None, ""):
            if registro is not None:
                sesion.delete(registro)
            continue
        try:
            hectareas = float(valor)
            if hectareas < 0:
                raise ValueError
        except (TypeError, ValueError):
            raise DatosInvalidos(
                "Ingresa superficies numéricas no negativas.",
                [{"campo": f"datos_501.superficies.{clave}",
                  "mensaje": "Ingresa una superficie válida y no negativa."}],
            )
        if registro is None:
            registro = SuperficieSolicitud(solicitud_id=solicitud_id, concepto_id=concepto.id,
                                           hectareas=hectareas)
            sesion.add(registro)
        else:
            registro.hectareas = hectareas
