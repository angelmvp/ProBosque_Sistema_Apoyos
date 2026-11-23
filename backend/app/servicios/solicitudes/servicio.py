"""Reglas de negocio para solicitudes y recepción."""
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.nucleo.excepciones import AccesoDenegado, Conflicto, DatosInvalidos, NoEncontrado
from app.servicios.archivos.almacenamiento import guardar_archivo
from app.servicios.archivos.modelos import Archivo
from app.servicios.autenticacion.modelos import Usuario
from app.servicios.bitacora.servicio import registrar
from app.servicios.catalogo.modelos import Municipio, Programa
from app.servicios.requisitos.modelos import DocumentoSolicitud, Requisito
from app.servicios.requisitos.servicio import asegurar_catalogo, faltantes
from app.servicios.solicitudes.modelos import Acuse, Folio, Recepcion, Solicitud
from app.servicios.expedientes.modelos import Expediente

ZONA = ZoneInfo("America/Mexico_City")
ESTADOS = ("borrador", "enviada", "recibida", "con_faltantes")


def _obtener(sesion: Session, solicitud_id: int) -> Solicitud:
    solicitud = sesion.get(Solicitud, solicitud_id)
    if solicitud is None:
        raise NoEncontrado("La solicitud no existe.")
    return solicitud


def exigir_propietario(sesion: Session, solicitud_id: int, usuario: Usuario) -> Solicitud:
    solicitud = _obtener(sesion, solicitud_id)
    if solicitud.solicitante_id != usuario.id:
        raise AccesoDenegado("La solicitud no pertenece a la persona autenticada.")
    return solicitud


def crear(sesion: Session, usuario: Usuario, programa_id: int, municipio_id: int) -> Solicitud:
    municipio = sesion.get(Municipio, municipio_id)
    if municipio is None:
        raise NoEncontrado("El municipio no existe.")
    programa = sesion.get(Programa, programa_id)
    if programa is None or not programa.solicitud_en_linea:
        raise DatosInvalidos("El programa no admite solicitudes en línea.")
    solicitud = Solicitud(solicitante_id=usuario.id, programa_id=programa_id,
                          municipio_id=municipio_id, region_id=municipio.region_id)
    sesion.add(solicitud)
    sesion.flush()
    asegurar_catalogo(sesion)
    registrar(sesion, accion="solicitud_creada", recurso=f"solicitud:{solicitud.id}",
              resultado="exitoso", usuario_id=usuario.id)
    return solicitud


def actualizar_formulario(sesion: Session, solicitud: Solicitud, *, datos_501: dict | None = None,
                          datos_502: dict | None = None, aviso_privacidad: bool | None = None) -> Solicitud:
    if solicitud.estado != "borrador":
        raise Conflicto("Solo se puede editar una solicitud en borrador.")
    if datos_501 is not None:
        solicitud.datos_501 = datos_501
    if datos_502 is not None:
        _validar_502(datos_502)
        solicitud.datos_502 = datos_502
        _marcar_502(sesion, solicitud.id)
    if aviso_privacidad is not None:
        solicitud.aviso_privacidad = aviso_privacidad
    return solicitud


def _validar_502(datos: dict) -> None:
    import re
    curp = datos.get("curp")
    if curp and len(curp) != 18:
        raise DatosInvalidos("La CURP debe tener 18 caracteres.")
    cp = datos.get("codigo_postal")
    if cp and not re.fullmatch(r"\d{5}", str(cp)):
        raise DatosInvalidos("El código postal debe tener 5 dígitos.")
    for campo in ("telefono_fijo", "telefono_celular"):
        valor = datos.get(campo)
        if valor and not re.fullmatch(r"\d{10}", str(valor)):
            raise DatosInvalidos(f"{campo} debe tener 10 dígitos.")
    correo = datos.get("correo_electronico")
    if correo and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", str(correo)):
        raise DatosInvalidos("El correo electrónico no es válido.")


def _marcar_502(sesion: Session, solicitud_id: int) -> None:
    requisito = sesion.scalar(select(Requisito).where(Requisito.clave == "registro_502"))
    if requisito:
        documento = sesion.get(DocumentoSolicitud, (solicitud_id, requisito.id))
        if documento is None:
            documento = DocumentoSolicitud(solicitud_id=solicitud_id, requisito_id=requisito.id)
            sesion.add(documento)
        documento.entregado = True


def agregar_documento(sesion: Session, solicitud: Solicitud, requisito_clave: str,
                      nombre: str, contenido: bytes, usuario: Usuario) -> DocumentoSolicitud:
    if solicitud.estado != "borrador":
        raise Conflicto("Solo se pueden modificar documentos en borradores.")
    requisito = sesion.scalar(select(Requisito).where(Requisito.clave == requisito_clave))
    if requisito is None:
        raise NoEncontrado("El requisito no existe.")
    archivo = guardar_archivo(sesion, nombre, contenido)
    documento = sesion.get(DocumentoSolicitud, (solicitud.id, requisito.id))
    if documento is None:
        documento = DocumentoSolicitud(solicitud_id=solicitud.id, requisito_id=requisito.id)
        sesion.add(documento)
    documento.archivo_id = archivo.id
    documento.entregado = True
    documento.observacion = ""
    registrar(sesion, accion="documento_agregado", recurso=f"solicitud:{solicitud.id}",
              resultado="exitoso", detalle=requisito_clave, usuario_id=usuario.id)
    return documento


def quitar_documento(sesion: Session, solicitud: Solicitud, requisito_clave: str,
                     usuario: Usuario) -> None:
    if solicitud.estado != "borrador":
        raise Conflicto("Solo se pueden modificar documentos en borradores.")
    requisito = sesion.scalar(select(Requisito).where(Requisito.clave == requisito_clave))
    if requisito is None:
        raise NoEncontrado("El requisito no existe.")
    documento = sesion.get(DocumentoSolicitud, (solicitud.id, requisito.id))
    if documento is None:
        raise NoEncontrado("El documento no existe.")
    documento.archivo_id = None
    documento.entregado = False
    documento.observacion = ""
    registrar(sesion, accion="documento_quitado", recurso=f"solicitud:{solicitud.id}",
              resultado="exitoso", detalle=requisito_clave, usuario_id=usuario.id)


def enviar(sesion: Session, solicitud: Solicitud, usuario: Usuario) -> Solicitud:
    if solicitud.estado != "borrador":
        raise Conflicto("La solicitud ya fue enviada.")
    if not solicitud.aviso_privacidad:
        raise DatosInvalidos("Debes aceptar el aviso de privacidad.")
    pendientes = faltantes(sesion, solicitud.id)
    if pendientes:
        raise DatosInvalidos("La solicitud tiene requisitos faltantes.")
    solicitud.estado = "enviada"
    solicitud.enviada_en = datetime.now(ZONA)
    registrar(sesion, accion="solicitud_enviada", recurso=f"solicitud:{solicitud.id}",
              resultado="exitoso", usuario_id=usuario.id)
    return solicitud


def listar_propias(sesion: Session, usuario: Usuario) -> list[Solicitud]:
    return list(sesion.scalars(select(Solicitud).where(Solicitud.solicitante_id == usuario.id)
                               .order_by(Solicitud.id.desc())))


def listar_para_recepcion(sesion: Session, usuario: Usuario) -> list[Solicitud]:
    consulta = select(Solicitud).where(Solicitud.estado.in_(("enviada", "con_faltantes")))
    if usuario.region_id is not None:
        consulta = consulta.where(Solicitud.region_id == usuario.region_id)
    return list(sesion.scalars(consulta.order_by(Solicitud.id.desc())))


def recibir(sesion: Session, solicitud: Solicitud, usuario: Usuario, observacion: str = "") -> Solicitud:
    if usuario.region_id is not None and solicitud.region_id != usuario.region_id:
        raise AccesoDenegado("La solicitud no pertenece a tu delegación.")
    pendientes = faltantes(sesion, solicitud.id)
    if pendientes:
        solicitud.estado = "con_faltantes"
        for pendiente in pendientes:
            requisito = sesion.scalar(select(Requisito).where(Requisito.clave == pendiente["clave"]))
            documento = sesion.get(DocumentoSolicitud, (solicitud.id, requisito.id))
            if documento:
                documento.observacion = observacion or "Documento pendiente de revisión."
        registrar(sesion, accion="solicitud_con_faltantes", recurso=f"solicitud:{solicitud.id}",
                  resultado="exitoso", usuario_id=usuario.id)
        return solicitud
    solicitud.estado = "recibida"
    solicitud.recibida_en = datetime.now(ZONA)
    sesion.add(Recepcion(solicitud_id=solicitud.id, receptor_id=usuario.id, observacion=observacion))
    folio = _crear_folio(sesion, solicitud)
    if sesion.scalar(select(Expediente).where(Expediente.folio == folio.valor)) is None:
        sesion.add(Expediente(folio=folio.valor, programa_id=solicitud.programa_id,
                              region_id=solicitud.region_id,
                              tramite=f"Solicitud {solicitud.id}"))
    solicitud._folio = folio
    registrar(sesion, accion="solicitud_recibida", recurso=f"solicitud:{solicitud.id}",
              resultado="exitoso", detalle=folio.valor, usuario_id=usuario.id)
    return solicitud


def _crear_folio(sesion: Session, solicitud: Solicitud) -> Folio:
    anio = datetime.now(ZONA).year
    ultimo = sesion.scalar(select(func.max(Folio.consecutivo)).where(Folio.anio == anio)) or 0
    consecutivo = int(ultimo) + 1
    folio = Folio(anio=anio, consecutivo=consecutivo, solicitud_id=solicitud.id,
                  valor=f"{consecutivo:05d}")
    sesion.add(folio)
    sesion.flush()
    return folio


def folio_de(sesion: Session, solicitud_id: int) -> Folio | None:
    return sesion.scalar(select(Folio).where(Folio.solicitud_id == solicitud_id))


def generar_acuse(sesion: Session, solicitud: Solicitud, usuario: Usuario) -> Acuse:
    if solicitud.estado != "recibida":
        raise Conflicto("Solo se puede generar acuse de una solicitud recibida.")
    existente = sesion.scalar(select(Acuse).where(Acuse.solicitud_id == solicitud.id))
    if existente:
        return existente
    folio = folio_de(sesion, solicitud.id)
    if folio is None:
        raise Conflicto("La solicitud todavía no tiene folio.")
    contenido = _pdf_acuse(folio.valor, solicitud.id, solicitud.programa.nombre, solicitud.municipio.nombre)
    archivo = guardar_archivo(sesion, f"acuse-{folio.valor}.pdf", contenido)
    acuse = Acuse(solicitud_id=solicitud.id, archivo_id=archivo.id)
    sesion.add(acuse)
    sesion.flush()
    registrar(sesion, accion="acuse_generado", recurso=f"solicitud:{solicitud.id}",
              resultado="exitoso", usuario_id=usuario.id)
    return acuse


def acuse_de(sesion: Session, solicitud_id: int) -> Acuse:
    acuse = sesion.scalar(select(Acuse).where(Acuse.solicitud_id == solicitud_id))
    if acuse is None:
        raise NoEncontrado("El acuse todavía no está disponible.")
    return acuse


def _pdf_acuse(folio: str, solicitud_id: int, programa: str, municipio: str) -> bytes:
    texto = f"PROBOSQUE - ACUSE DE RECEPCION | Folio: {folio} | Solicitud: {solicitud_id} | {programa} | {municipio}"
    cuerpo = f"BT /F1 10 Tf 40 760 Td ({texto[:180]}) Tj ET".encode("latin-1", "replace")
    return (b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            b"2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n"
            b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Resources<</Font<</F1 4 0 R>>>>/Contents 5 0 R>>endobj\n"
            b"4 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
            + f"5 0 obj<</Length {len(cuerpo)}>>stream\n".encode() + cuerpo
            + b"\nendstream endobj\ntrailer<</Root 1 0 R>>\n%%EOF")
