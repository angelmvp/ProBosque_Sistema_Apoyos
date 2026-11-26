"""Pruebas de aceptación de HU-04 a HU-07."""
import io


def _borrador(como, programa="capturando_carbono", municipio_nombre="Toluca"):
    cliente = como("solicitante")
    programas = cliente.get("/api/solicitudes/catalogos/programas").json()
    municipios = cliente.get("/api/solicitudes/catalogos/municipios").json()
    programa_id = next(item["id"] for item in programas if item["clave"] == programa)
    municipio = next(item for item in municipios if item["nombre"] == municipio_nombre)
    respuesta = cliente.post("/api/solicitudes", json={
        "programa_id": programa_id, "municipio_id": municipio["id"],
    })
    assert respuesta.status_code == 201, respuesta.text
    return cliente, respuesta.json()["id"]


def _datos_501(tipo_persona="propietario"):
    datos = {
        "tipo_persona": tipo_persona,
        "denominacion": "Comunidad de prueba" if tipo_persona == "nucleo_agrario" else "",
        "personas": {"solicitante": {"nombre": "Sofía", "primer_apellido": "Prueba"}},
        "grupos": ["Ninguno"],
        "predio_nombre": "Predio de prueba",
        "poblacion_localidad": "Localidad de prueba",
        "superficie_total": "5",
        "superficies": {},
        "declaratoria_no_litigio": True,
    }
    return datos


def _datos_502():
    return {
        "primer_apellido": "Prueba", "segundo_apellido": "Ejemplo", "nombres": "Sofía",
        "fecha_nacimiento": "1980-01-02", "sexo": "M", "estado_civil": "Soltera",
        "grado_estudios": "Licenciatura", "tipo_identificacion": "INE",
        "folio_identificacion": "123456789", "nacionalidad": "Mexicana",
        "entidad_nacimiento": "Estado de México", "curp": "AAAA000000HDFBBB01",
        "telefono_celular": "5512345678", "correo_electronico": "solicitante@probosque.test",
        "calle": "Calle de prueba", "numero_exterior": "10", "colonia": "Centro",
        "localidad": "Toluca", "municipio": "Toluca", "entidad": "Estado de México",
        "codigo_postal": "52140", "lugar_fecha": "Toluca, 2026",
        "nombre_beneficiario": "Sofía Prueba Ejemplo",
    }


def _completar(cliente, solicitud_id, pdf):
    respuesta = cliente.put(f"/api/solicitudes/{solicitud_id}", json={
        "datos_501": _datos_501(),
        "datos_502": _datos_502(),
        "aviso_privacidad": True,
    })
    assert respuesta.status_code == 200, respuesta.text
    for requisito in ("identificacion", "curp", "propiedad", "registro_plantacion"):
        respuesta = cliente.post(f"/api/solicitudes/{solicitud_id}/documentos",
                                 data={"requisito": requisito},
                                 files={"archivo": ("documento.pdf", io.BytesIO(pdf), "application/pdf")})
        assert respuesta.status_code == 200, respuesta.text
    assert cliente.post(f"/api/solicitudes/{solicitud_id}/pasos/2/validar").status_code == 200


def test_hu04_ca1_crea_borrador_y_conserva_datos(como):
    """HU-04-CA-1: la persona puede crear un borrador de solicitud."""
    cliente, solicitud_id = _borrador(como)
    respuesta = cliente.get(f"/api/solicitudes/{solicitud_id}")
    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "borrador"
    assert respuesta.json()["folio"] is None


def test_hu04_ca2_valida_y_devuelve_errores_por_campo(como):
    """HU-04-CA-2: errores de CURP y campos se devuelven en el contrato 422."""
    cliente, solicitud_id = _borrador(como)
    respuesta = cliente.put(f"/api/solicitudes/{solicitud_id}", json={
        "datos_502": {"curp": "corta", "codigo_postal": "x", "telefono_celular": "1"},
    })
    assert respuesta.status_code == 422
    assert respuesta.json()["codigo"] == "datos_invalidos"
    assert {campo["campo"] for campo in respuesta.json()["campos"]} == {
        "datos_502.curp", "datos_502.codigo_postal", "datos_502.telefono_celular",
    }


def test_hu04_ca2_valida_solicitud_unica(como):
    """HU-04-CA-2: la solicitud única requiere persona, superficie y declaratoria."""
    cliente, solicitud_id = _borrador(como)
    respuesta = cliente.post(f"/api/solicitudes/{solicitud_id}/pasos/1/validar")
    assert respuesta.status_code == 422
    campos = {item["campo"] for item in respuesta.json()["campos"]}
    assert "datos_501.superficie_total" in campos
    assert "datos_501.declaratoria_no_litigio" in campos


def test_hu05_ca1_muestra_checklist_condicional(como):
    """HU-05-CA-1: el checklist es sensible al programa y tipo de persona."""
    cliente, solicitud_id = _borrador(como)
    cliente.put(f"/api/solicitudes/{solicitud_id}", json={"datos_501": _datos_501("nucleo_agrario")})
    requisitos = cliente.get(f"/api/solicitudes/{solicitud_id}/requisitos").json()
    por_clave = {item["clave"]: item for item in requisitos}
    assert por_clave["acta_incorporacion"]["aplica"] is True
    assert por_clave["acta_representacion"]["aplica"] is True
    assert por_clave["constitucion"]["aplica"] is False
    assert por_clave["registro_plantacion"]["aplica"] is True


def test_hu05_ca2_bloquea_envio_incompleto_y_nombra_faltantes(como):
    """HU-05-CA-2: una solicitud incompleta puede guardarse, pero no enviarse."""
    cliente, solicitud_id = _borrador(como)
    respuesta = cliente.post(f"/api/solicitudes/{solicitud_id}/enviar")
    assert respuesta.status_code == 422
    assert any("Identificación oficial" in item["mensaje"]
               for item in respuesta.json()["campos"])


def test_documento_502_solo_se_entrega_al_completar_y_validar(como):
    cliente, solicitud_id = _borrador(como)
    cliente.put(f"/api/solicitudes/{solicitud_id}", json={
        "datos_502": {"curp": "AAAA000000HDFBBB01"}, "aviso_privacidad": True,
    })
    requisitos = cliente.get(f"/api/solicitudes/{solicitud_id}/requisitos").json()
    assert next(item for item in requisitos if item["clave"] == "registro_502")["entregado"] is False

    cliente.put(f"/api/solicitudes/{solicitud_id}", json={
        "datos_502": _datos_502(), "aviso_privacidad": True,
    })
    assert cliente.post(f"/api/solicitudes/{solicitud_id}/pasos/2/validar").status_code == 200
    requisitos = cliente.get(f"/api/solicitudes/{solicitud_id}/requisitos").json()
    assert next(item for item in requisitos if item["clave"] == "registro_502")["entregado"] is True


def test_documentos_solicitud_rechazan_docx_y_firmas_invalidas(como):
    cliente, solicitud_id = _borrador(como)
    respuesta = cliente.post(f"/api/solicitudes/{solicitud_id}/documentos",
                             data={"requisito": "identificacion"},
                             files={"archivo": ("identificacion.docx", io.BytesIO(b"no docx"),
                                                "application/vnd.openxmlformats-officedocument.wordprocessingml.document")})
    assert respuesta.status_code == 422
    assert "PDF, JPG y PNG" in respuesta.json()["mensaje"]

    respuesta = cliente.post(f"/api/solicitudes/{solicitud_id}/documentos",
                             data={"requisito": "identificacion"},
                             files={"archivo": ("identificacion.pdf", io.BytesIO(b"no pdf"), "application/pdf")})
    assert respuesta.status_code == 422
    assert "firma PDF" in respuesta.json()["mensaje"]


def test_hu06_ca1_envia_y_fija_fecha(como, pdf_valido):
    """HU-06-CA-1: enviar registra la fecha y cambia el estado."""
    cliente, solicitud_id = _borrador(como)
    _completar(cliente, solicitud_id, pdf_valido)
    respuesta = cliente.post(f"/api/solicitudes/{solicitud_id}/enviar")
    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "enviada"
    assert respuesta.json()["enviada_en"]


def test_hu06_ca2_no_envia_con_faltantes(como):
    """HU-06-CA-2: los requisitos pendientes impiden el envío."""
    cliente, solicitud_id = _borrador(como)
    respuesta = cliente.post(f"/api/solicitudes/{solicitud_id}/enviar")
    assert respuesta.status_code == 422
    assert respuesta.json()["campos"]


def test_hu07_ca1_filtra_por_delegacion(como):
    """HU-07-CA-1: la delegación solo puede recibir solicitudes de su región."""
    cliente, solicitud_id = _borrador(como, municipio_nombre="Acambay")
    _completar(cliente, solicitud_id, b"%PDF-1.4\ncontenido")
    cliente.post(f"/api/solicitudes/{solicitud_id}/enviar")
    delegacion = como("delegacion.toluca")
    respuesta = delegacion.get(f"/api/recepcion/solicitudes/{solicitud_id}")
    assert respuesta.status_code == 403


def test_hu07_ca2_solicitud_con_faltantes_no_genera_folio_ni_acuse(como, pdf_valido):
    cliente, solicitud_id = _borrador(como)
    _completar(cliente, solicitud_id, pdf_valido)
    cliente.post(f"/api/solicitudes/{solicitud_id}/enviar")
    delegacion = como("delegacion.toluca")
    respuesta = delegacion.post(f"/api/recepcion/solicitudes/{solicitud_id}/recibir", json={
        "solicitud_completa": False, "documentos_legibles": True,
        "corresponden_al_programa": True,
        "faltantes": [{"requisito": "curp", "observacion": "La CURP no es legible."}],
    })
    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "con_faltantes"
    assert respuesta.json()["folio"] is None
    assert respuesta.json()["acuse_disponible"] is False


def test_hu07_ca2_recibe_genera_folio_y_acuse_inmutable(como, pdf_valido):
    """HU-07-CA-2: recepción completa crea folio, expediente y acuse persistente."""
    cliente, solicitud_id = _borrador(como)
    _completar(cliente, solicitud_id, pdf_valido)
    assert cliente.post(f"/api/solicitudes/{solicitud_id}/enviar").status_code == 200
    delegacion = como("delegacion.toluca")
    respuesta = delegacion.post(f"/api/recepcion/solicitudes/{solicitud_id}/recibir", json={
        "solicitud_completa": True, "documentos_legibles": True,
        "corresponden_al_programa": True,
    })
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["estado"] == "recibida"
    assert len(respuesta.json()["folio"]) == 5
    assert respuesta.json()["acuse_disponible"] is True
    acuse_1 = cliente.get(f"/api/solicitudes/{solicitud_id}/acuse")
    acuse_2 = cliente.get(f"/api/solicitudes/{solicitud_id}/acuse")
    assert acuse_1.status_code == 200
    assert acuse_1.content == acuse_2.content
    assert b"ACUSE DE RECEPCI\xd3N" in acuse_1.content
    assert b"/WinAnsiEncoding" in acuse_1.content
    assert b"startxref\n" in acuse_1.content
    assert respuesta.json()["folio"].encode() in acuse_1.content
    vista = delegacion.get(f"/api/recepcion/solicitudes/{solicitud_id}/acuse/archivo")
    assert vista.status_code == 200
    assert vista.headers["content-disposition"] == "inline"
