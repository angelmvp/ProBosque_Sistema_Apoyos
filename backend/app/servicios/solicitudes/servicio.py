"""Reglas de negocio para solicitudes y recepción."""
from datetime import datetime
import re
import textwrap
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.nucleo.excepciones import AccesoDenegado, Conflicto, DatosInvalidos, NoEncontrado
from app.servicios.archivos.almacenamiento import guardar_documento_solicitud, guardar_archivo
from app.servicios.archivos.modelos import Archivo
from app.servicios.autenticacion.modelos import Usuario
from app.servicios.bitacora.servicio import registrar
from app.servicios.catalogo.modelos import Municipio, Programa
from app.servicios.requisitos.modelos import DocumentoSolicitud, Requisito
from app.servicios.requisitos.servicio import (
    asegurar_catalogo, checklist, faltantes, guardar_superficies,
)
from app.servicios.solicitudes.modelos import Acuse, ContadorFolio, Folio, Recepcion, Solicitud
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
        asegurar_catalogo(sesion)
        guardar_superficies(sesion, solicitud.id, datos_501, solicitud.programa.clave)
    if datos_502 is not None:
        _validar_formatos_502(datos_502)
        solicitud.datos_502 = datos_502
        asegurar_catalogo(sesion)
        requisito_502 = sesion.scalar(select(Requisito).where(Requisito.clave == "registro_502"))
        registro_502 = sesion.get(DocumentoSolicitud, (solicitud.id, requisito_502.id))
        if registro_502:
            registro_502.entregado = False
    if aviso_privacidad is not None:
        solicitud.aviso_privacidad = aviso_privacidad
    return solicitud


def _error_campos(errores: list[dict[str, str]], mensaje: str) -> None:
    if errores:
        raise DatosInvalidos(mensaje, errores)


def _exigir(datos: dict, campos: tuple[str, ...], prefijo: str) -> list[dict[str, str]]:
    return [{"campo": f"{prefijo}.{campo}", "mensaje": "Campo obligatorio"}
            for campo in campos if not str(datos.get(campo, "")).strip()]


def validar_501(solicitud: Solicitud) -> None:
    datos = solicitud.datos_501 or {}
    errores: list[dict[str, str]] = []
    tipo = datos.get("tipo_persona", "")
    tipos = {"propietario", "poseedor", "nucleo_agrario", "sociedad", "otro"}
    if tipo not in tipos:
        errores.append({"campo": "datos_501.tipo_persona", "mensaje": "Selecciona un tipo de persona."})
    if tipo == "otro" and not str(datos.get("tipo_persona_otro", "")).strip():
        errores.append({"campo": "datos_501.tipo_persona_otro", "mensaje": "Campo obligatorio"})
    if tipo in {"nucleo_agrario", "sociedad"} and not str(datos.get("denominacion", "")).strip():
        errores.append({"campo": "datos_501.denominacion", "mensaje": "Campo obligatorio"})
    personas = datos.get("personas") or {}
    persona = personas.get("solicitante", {}) if isinstance(personas, dict) else {}
    for campo in ("nombre", "primer_apellido"):
        if not str(persona.get(campo, "")).strip():
            errores.append({"campo": f"datos_501.personas.solicitante.{campo}",
                            "mensaje": "Campo obligatorio"})
    grupos = datos.get("grupos")
    if not isinstance(grupos, list) or not grupos:
        errores.append({"campo": "datos_501.grupos", "mensaje": "Selecciona al menos una opción."})
    elif "Ninguno" in grupos and len(grupos) > 1:
        errores.append({"campo": "datos_501.grupos", "mensaje": "Ninguno no puede combinarse con otros grupos."})
    for campo in ("predio_nombre", "poblacion_localidad"):
        if not str(datos.get(campo, "")).strip():
            errores.append({"campo": f"datos_501.{campo}", "mensaje": "Campo obligatorio"})
    superficie = datos.get("superficie_total")
    try:
        superficie_total = float(superficie)
        if superficie_total <= 0:
            raise ValueError
    except (TypeError, ValueError):
        superficie_total = 0
        errores.append({"campo": "datos_501.superficie_total",
                        "mensaje": "La superficie total debe ser mayor que cero."})
    if not datos.get("declaratoria_no_litigio"):
        errores.append({"campo": "datos_501.declaratoria_no_litigio",
                        "mensaje": "Debes aceptar la declaratoria."})

    superficies = datos.get("superficies", {})
    if not isinstance(superficies, dict):
        superficies = {}
        errores.append({"campo": "datos_501.superficies", "mensaje": "Ingresa conceptos de superficie válidos."})
    suma = 0.0
    for clave, valor in superficies.items():
        if valor in (None, ""):
            continue
        try:
            hectareas = float(valor)
            if hectareas < 0:
                raise ValueError
            suma += hectareas
        except (TypeError, ValueError):
            errores.append({"campo": f"datos_501.superficies.{clave}",
                            "mensaje": "Ingresa una superficie válida y no negativa."})
    if superficie_total and suma > superficie_total:
        errores.append({"campo": "datos_501.superficies",
                        "mensaje": "La suma de conceptos no puede superar la superficie total."})
    tipo_certificado = datos.get("cuenta_certificado")
    if tipo_certificado == "si" and not str(datos.get("tipo_certificado", "")).strip():
        errores.append({"campo": "datos_501.tipo_certificado", "mensaje": "Campo obligatorio"})
    if datos.get("otro_programa_beneficiado") == "si" and not str(
        datos.get("otro_programa_detalle", "")
    ).strip():
        errores.append({"campo": "datos_501.otro_programa_detalle", "mensaje": "Campo obligatorio"})
    _error_campos(errores, "Revisa los campos obligatorios de la Solicitud Única.")


def _validar_formatos_502(datos: dict) -> None:
    errores: list[dict[str, str]] = []
    curp = str(datos.get("curp", "")).strip().upper()
    if curp and not re.fullmatch(r"[A-Z]{4}\d{6}[HM][A-Z]{5}[A-Z0-9]\d", curp):
        errores.append({"campo": "datos_502.curp", "mensaje": "Ingresa una CURP válida de 18 caracteres."})
    domicilio = datos.get("domicilio") or {}
    if not isinstance(domicilio, dict):
        domicilio = {}
    cp = str(datos.get("codigo_postal", domicilio.get("codigo_postal", ""))).strip()
    if cp and not re.fullmatch(r"\d{5}", cp):
        errores.append({"campo": "datos_502.codigo_postal", "mensaje": "El código postal debe tener 5 dígitos."})
    for campo in ("telefono_fijo", "telefono_celular"):
        valor = str(datos.get(campo, "")).strip()
        if valor and not re.fullmatch(r"\d{10}", valor):
            errores.append({"campo": f"datos_502.{campo}", "mensaje": "Debe contener 10 dígitos."})
    correo = str(datos.get("correo_electronico", "")).strip()
    if correo and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", correo):
        errores.append({"campo": "datos_502.correo_electronico", "mensaje": "Ingresa un correo válido."})
    _error_campos(errores, "Revisa los datos del Registro de Información.")


def validar_502(sesion: Session, solicitud: Solicitud, *, marcar: bool = True) -> None:
    datos = solicitud.datos_502 or {}
    requeridos = (
        "primer_apellido", "segundo_apellido", "nombres", "fecha_nacimiento", "sexo", "estado_civil",
        "grado_estudios", "tipo_identificacion", "folio_identificacion", "nacionalidad",
        "entidad_nacimiento", "curp", "telefono_celular", "correo_electronico",
        "calle", "numero_exterior", "colonia", "localidad", "municipio", "entidad",
        "codigo_postal", "lugar_fecha", "nombre_beneficiario",
    )
    errores = _exigir(datos, requeridos, "datos_502")
    if not solicitud.aviso_privacidad:
        errores.append({"campo": "aviso_privacidad", "mensaje": "Debes aceptar el aviso de privacidad."})
    if datos.get("curp") and not re.fullmatch(
        r"[A-Z]{4}\d{6}[HM][A-Z]{5}[A-Z0-9]\d", str(datos["curp"]).upper()
    ):
        errores.append({"campo": "datos_502.curp", "mensaje": "Ingresa una CURP válida de 18 caracteres."})
    if datos.get("codigo_postal") and not re.fullmatch(r"\d{5}", str(datos["codigo_postal"])):
        errores.append({"campo": "datos_502.codigo_postal", "mensaje": "El código postal debe tener 5 dígitos."})
    if datos.get("telefono_celular") and not re.fullmatch(r"\d{10}", str(datos["telefono_celular"])):
        errores.append({"campo": "datos_502.telefono_celular", "mensaje": "Debe contener 10 dígitos."})
    if datos.get("correo_electronico") and not re.fullmatch(
        r"[^@\s]+@[^@\s]+\.[^@\s]+", str(datos["correo_electronico"])
    ):
        errores.append({"campo": "datos_502.correo_electronico", "mensaje": "Ingresa un correo válido."})
    if datos.get("fecha_nacimiento"):
        try:
            datetime.strptime(str(datos["fecha_nacimiento"]), "%Y-%m-%d")
        except ValueError:
            errores.append({"campo": "datos_502.fecha_nacimiento",
                            "mensaje": "Usa el formato de fecha AAAA-MM-DD."})
    if datos.get("sexo") and datos["sexo"] not in {"H", "M"}:
        errores.append({"campo": "datos_502.sexo", "mensaje": "Selecciona H o M."})
    _error_campos(errores, "Completa los campos obligatorios del Registro de Información.")
    if marcar:
        asegurar_catalogo(sesion)
        _marcar_502(sesion, solicitud.id)


def validar_paso(sesion: Session, solicitud: Solicitud, paso: int) -> None:
    if solicitud.estado != "borrador":
        raise Conflicto("La solicitud ya no se puede editar.")
    if paso == 1:
        validar_501(solicitud)
    elif paso == 2:
        validar_502(sesion, solicitud)
    elif paso in {3, 4}:
        requisitos = checklist(
            sesion, solicitud.id, solicitud.programa.clave,
            (solicitud.datos_501 or {}).get("tipo_persona", ""), solicitud.datos_501,
        )
        grupos = {"identidad_representacion"} if paso == 3 else {"propiedad_modalidad", "programa"}
        faltantes_paso = [
            item for item in requisitos
            if item["aplica"] and item["obligatorio"] and item["grupo"] in grupos and not item["entregado"]
        ]
        _error_campos(
            [{"campo": f"documentos.{item['clave']}", "mensaje": f"Falta adjuntar: {item['nombre']}."}
             for item in faltantes_paso],
            "Completa los documentos obligatorios de este paso.",
        )
    elif paso == 5:
        validar_501(solicitud)
        validar_502(sesion, solicitud)
        pendientes = faltantes(
            sesion, solicitud.id, solicitud.programa.clave,
            (solicitud.datos_501 or {}).get("tipo_persona", ""), solicitud.datos_501,
        )
        _error_campos(
            [{"campo": f"documentos.{item['clave']}", "mensaje": f"Falta adjuntar: {item['nombre']}."}
             for item in pendientes],
            "La solicitud tiene documentos obligatorios pendientes.",
        )
    else:
        raise DatosInvalidos("El paso solicitado no es válido.")


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
    if requisito.clave == "registro_502":
        raise DatosInvalidos("El FO-PB-502 se completa en línea y no se adjunta.")
    estado = next((item for item in checklist(
        sesion, solicitud.id, solicitud.programa.clave,
        (solicitud.datos_501 or {}).get("tipo_persona", ""), solicitud.datos_501,
    ) if item["clave"] == requisito_clave), None)
    if not estado or not estado["aplica"]:
        raise DatosInvalidos("Este documento no aplica al programa o tipo de persona seleccionado.")
    archivo = guardar_documento_solicitud(sesion, nombre, contenido)
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
    if requisito.clave == "registro_502":
        raise DatosInvalidos("El FO-PB-502 se completa en línea y no se puede quitar.")
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
    validar_501(solicitud)
    validar_502(sesion, solicitud)
    pendientes = faltantes(
        sesion, solicitud.id, solicitud.programa.clave,
        (solicitud.datos_501 or {}).get("tipo_persona", ""), solicitud.datos_501,
    )
    if pendientes:
        raise DatosInvalidos(
            "La solicitud tiene documentos obligatorios pendientes.",
            [{"campo": f"documentos.{item['clave']}",
              "mensaje": f"Falta adjuntar: {item['nombre']}."} for item in pendientes],
        )
    solicitud.estado = "enviada"
    solicitud.enviada_en = datetime.now(ZONA)
    registrar(sesion, accion="solicitud_enviada", recurso=f"solicitud:{solicitud.id}",
              resultado="exitoso", usuario_id=usuario.id)
    return solicitud


def listar_propias(sesion: Session, usuario: Usuario) -> list[Solicitud]:
    return list(sesion.scalars(select(Solicitud).where(Solicitud.solicitante_id == usuario.id)
                               .order_by(Solicitud.id.desc())))


def listar_para_recepcion(sesion: Session, usuario: Usuario) -> list[Solicitud]:
    consulta = select(Solicitud).where(Solicitud.estado.in_(("enviada", "con_faltantes", "recibida")))
    if usuario.region_id is not None:
        consulta = consulta.where(Solicitud.region_id == usuario.region_id)
    return list(sesion.scalars(consulta.order_by(Solicitud.id.desc())))


def recibir(sesion: Session, solicitud: Solicitud, usuario: Usuario, *,
            observacion: str = "", solicitud_completa: bool = False,
            documentos_legibles: bool = False, corresponden_al_programa: bool = False,
            documentos_faltantes: list[dict[str, str]] | None = None) -> Solicitud:
    if usuario.region_id is not None and solicitud.region_id != usuario.region_id:
        raise AccesoDenegado("La solicitud no pertenece a tu delegación.")
    if solicitud.estado not in {"enviada", "con_faltantes"}:
        raise Conflicto("Solo se pueden revisar solicitudes enviadas o con faltantes.")
    asegurar_catalogo(sesion)
    pendientes = faltantes(
        sesion, solicitud.id, solicitud.programa.clave,
        (solicitud.datos_501 or {}).get("tipo_persona", ""), solicitud.datos_501,
    )
    documentos_faltantes = documentos_faltantes or []
    observaciones_por_requisito = {
        item.get("requisito", ""): item.get("observacion", "").strip()
        for item in documentos_faltantes
    }
    for clave, detalle in observaciones_por_requisito.items():
        requisito = sesion.scalar(select(Requisito).where(Requisito.clave == clave))
        if requisito is None:
            raise DatosInvalidos(f"El requisito {clave} no existe.")
        documento = sesion.get(DocumentoSolicitud, (solicitud.id, requisito.id))
        if documento is None:
            documento = DocumentoSolicitud(solicitud_id=solicitud.id, requisito_id=requisito.id)
            sesion.add(documento)
        documento.entregado = False
        documento.observacion = detalle or "Documento faltante o no cumple."
    pendientes_claves = {item["clave"] for item in pendientes}
    faltantes_de_revision = bool(observaciones_por_requisito or pendientes_claves)
    revision_completa = solicitud_completa and documentos_legibles and corresponden_al_programa
    if faltantes_de_revision or not revision_completa:
        solicitud.estado = "con_faltantes"
        detalle = observacion or "La Delegación registró documentos faltantes o pendientes de revisión."
        recepcion = sesion.scalar(select(Recepcion).where(Recepcion.solicitud_id == solicitud.id))
        if recepcion is None:
            recepcion = Recepcion(solicitud_id=solicitud.id, receptor_id=usuario.id)
            sesion.add(recepcion)
        recepcion.receptor_id = usuario.id
        recepcion.observacion = detalle
        recepcion.solicitud_completa = solicitud_completa
        recepcion.documentos_legibles = documentos_legibles
        recepcion.corresponden_al_programa = corresponden_al_programa
        registrar(sesion, accion="solicitud_con_faltantes", recurso=f"solicitud:{solicitud.id}",
                  resultado="exitoso", detalle=detalle, usuario_id=usuario.id)
        return solicitud
    solicitud.estado = "recibida"
    solicitud.recibida_en = datetime.now(ZONA)
    recepcion = sesion.scalar(select(Recepcion).where(Recepcion.solicitud_id == solicitud.id))
    if recepcion is None:
        recepcion = Recepcion(solicitud_id=solicitud.id, receptor_id=usuario.id)
        sesion.add(recepcion)
    recepcion.receptor_id = usuario.id
    recepcion.observacion = observacion
    recepcion.solicitud_completa = solicitud_completa
    recepcion.documentos_legibles = documentos_legibles
    recepcion.corresponden_al_programa = corresponden_al_programa
    folio = _crear_folio(sesion, solicitud)
    if sesion.scalar(select(Expediente).where(Expediente.folio == folio.valor)) is None:
        sesion.add(Expediente(folio=folio.valor, programa_id=solicitud.programa_id,
                              region_id=solicitud.region_id,
                              tramite=f"Solicitud {solicitud.id}"))
    solicitud._folio = folio
    generar_acuse(sesion, solicitud, usuario)
    registrar(sesion, accion="solicitud_recibida", recurso=f"solicitud:{solicitud.id}",
              resultado="exitoso", detalle=folio.valor, usuario_id=usuario.id)
    return solicitud


def _crear_folio(sesion: Session, solicitud: Solicitud) -> Folio:
    sesion.execute(select(Solicitud.id).where(Solicitud.id == solicitud.id).with_for_update())
    existente = folio_de(sesion, solicitud.id)
    if existente:
        return existente
    anio = datetime.now(ZONA).year
    sesion.execute(
        pg_insert(ContadorFolio)
        .values(anio=anio, consecutivo=1)
        .on_conflict_do_update(
            index_elements=[ContadorFolio.anio],
            set_={"consecutivo": ContadorFolio.consecutivo + 1},
        )
    )
    consecutivo = sesion.scalar(
        select(ContadorFolio.consecutivo).where(ContadorFolio.anio == anio)
    )
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
    contenido = _pdf_acuse(sesion, folio.valor, solicitud)
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


def _pdf_acuse(sesion: Session, folio: str, solicitud: Solicitud) -> bytes:
    nombre = solicitud.solicitante.nombre_completo if hasattr(solicitud.solicitante, "nombre_completo") else (
        f"{solicitud.solicitante.nombre} {solicitud.solicitante.apellido_paterno or ''} "
        f"{solicitud.solicitante.apellido_materno or ''}"
    )
    requisitos = checklist(
        sesion, solicitud.id, solicitud.programa.clave,
        (solicitud.datos_501 or {}).get("tipo_persona", ""), solicitud.datos_501,
    )
    documentos = [f"Documento {item['numero']}: {item['nombre']}"
                  for item in requisitos if item["aplica"] and item["entregado"]]
    fecha = (solicitud.recibida_en or datetime.now(ZONA)).astimezone(ZONA).strftime("%d/%m/%Y %H:%M")
    datos = solicitud.datos_501 or {}
    lineas = [
        "PROBOSQUE - ACUSE DE RECEPCIÓN",
        f"Folio: {folio}    Fecha y hora: {fecha}",
        f"Programa: {solicitud.programa.nombre}",
        f"Persona solicitante: {nombre.strip()}",
        f"Predio: {datos.get('predio_nombre', 'No especificado')}",
        f"Municipio: {solicitud.municipio.nombre}",
        f"Delegación: {solicitud.region.nombre}",
        "Documentos presentados:",
        *documentos,
        "El trámite es gratuito.",
        "La recepción no implica compromiso de otorgar el apoyo.",
    ]
    def literal_pdf(texto: str) -> bytes:
        contenido = texto.encode("cp1252", "replace")
        contenido = contenido.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")
        return b"(" + contenido + b")"

    lineas_envueltas = [
        fragmento
        for linea in lineas
        for fragmento in (textwrap.wrap(linea, width=95) or [""])
    ]
    comandos = [b"BT /F1 10 Tf 42 752 Td 13 TL"]
    for indice, linea in enumerate(lineas_envueltas):
        if indice:
            comandos.append(b"T*")
        comandos.append(literal_pdf(linea) + b" Tj")
    comandos.append(b"ET")
    cuerpo = b"\n".join(comandos)
    objetos = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Count 1 /Kids [3 0 R] >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        f"<< /Length {len(cuerpo)} >>\nstream\n".encode("ascii") + cuerpo + b"\nendstream",
    ]
    pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for numero, objeto in enumerate(objetos, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{numero} 0 obj\n".encode("ascii"))
        pdf.extend(objeto)
        pdf.extend(b"\nendobj\n")
    inicio_xref = len(pdf)
    pdf.extend(f"xref\n0 {len(objetos) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        f"trailer\n<< /Size {len(objetos) + 1} /Root 1 0 R >>\n"
        f"startxref\n{inicio_xref}\n%%EOF\n".encode("ascii")
    )
    return bytes(pdf)
