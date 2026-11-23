"""Pruebas de aceptación de HU-04 a HU-07."""
import io


def _borrador(como):
    cliente = como("solicitante")
    programas = cliente.get("/api/solicitudes/catalogos/programas").json()
    municipios = cliente.get("/api/solicitudes/catalogos/municipios").json()
    municipio = next(item for item in municipios if item["nombre"] == "Toluca")
    respuesta = cliente.post("/api/solicitudes", json={
        "programa_id": programas[0]["id"], "municipio_id": municipio["id"],
    })
    assert respuesta.status_code == 201, respuesta.text
    return cliente, respuesta.json()["id"]


def _completar(cliente, solicitud_id, pdf):
    respuesta = cliente.put(f"/api/solicitudes/{solicitud_id}", json={
        "datos_501": {"predio": "Predio de prueba"},
        "datos_502": {"curp": "AAAA000000HDFBBB01", "codigo_postal": "52140",
                      "telefono_celular": "5512345678"},
        "aviso_privacidad": True,
    })
    assert respuesta.status_code == 200, respuesta.text
    for requisito in ("identificacion", "curp", "propiedad"):
        respuesta = cliente.post(f"/api/solicitudes/{solicitud_id}/documentos",
                                 data={"requisito": requisito},
                                 files={"archivo": ("documento.pdf", io.BytesIO(pdf), "application/pdf")})
        assert respuesta.status_code == 200, respuesta.text


def test_hu04_ca1_crea_borrador_y_conserva_datos(como):
    """HU-04-CA-1: la persona puede crear un borrador de solicitud."""
    cliente, solicitud_id = _borrador(como)
    respuesta = cliente.get(f"/api/solicitudes/{solicitud_id}")
    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "borrador"


def test_hu04_ca2_valida_datos_del_502(como):
    """HU-04-CA-2: CURP, código postal y teléfono tienen validación."""
    cliente, solicitud_id = _borrador(como)
    respuesta = cliente.put(f"/api/solicitudes/{solicitud_id}", json={
        "datos_502": {"curp": "corta", "codigo_postal": "x", "telefono_celular": "1"},
    })
    assert respuesta.status_code == 422


def test_hu05_ca1_muestra_checklist(como):
    """HU-05-CA-1: el checklist distingue requisitos entregados y faltantes."""
    cliente, solicitud_id = _borrador(como)
    requisitos = cliente.get(f"/api/solicitudes/{solicitud_id}/requisitos").json()
    assert requisitos and all("entregado" in requisito for requisito in requisitos)


def test_hu05_ca2_bloquea_envio_incompleto(como):
    """HU-05-CA-2: una solicitud incompleta no se puede enviar."""
    cliente, solicitud_id = _borrador(como)
    assert cliente.put(f"/api/solicitudes/{solicitud_id}",
                       json={"aviso_privacidad": True}).status_code == 200
    assert cliente.post(f"/api/solicitudes/{solicitud_id}/enviar").status_code == 422


def test_hu06_ca1_envia_y_fija_fecha(como, pdf_valido):
    """HU-06-CA-1: enviar registra la fecha y cambia el estado."""
    cliente, solicitud_id = _borrador(como)
    _completar(cliente, solicitud_id, pdf_valido)
    respuesta = cliente.post(f"/api/solicitudes/{solicitud_id}/enviar")
    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "enviada"
    assert respuesta.json()["enviada_en"]


def test_hu06_ca2_no_envia_sin_requisitos(como):
    """HU-06-CA-2: el envío devuelve faltantes si no están completos."""
    cliente, solicitud_id = _borrador(como)
    assert cliente.post(f"/api/solicitudes/{solicitud_id}/enviar").status_code == 422


def test_hu07_ca1_filtra_por_delegacion(como):
    """HU-07-CA-1: la delegación solo puede recibir solicitudes de su región."""
    cliente = como("solicitante")
    programa = cliente.get("/api/solicitudes/catalogos/programas").json()[0]
    municipio = next(item for item in cliente.get("/api/solicitudes/catalogos/municipios").json()
                      if item["nombre"] == "Acambay")
    solicitud_id = cliente.post("/api/solicitudes", json={
        "programa_id": programa["id"], "municipio_id": municipio["id"],
    }).json()["id"]
    delegacion = como("delegacion.toluca")
    respuesta = delegacion.post(f"/api/recepcion/solicitudes/{solicitud_id}/recibir", json={})
    assert respuesta.status_code == 403


def test_hu07_ca2_recibe_y_genera_folio(como, pdf_valido):
    """HU-07-CA-2: una recepción completa genera un folio anual."""
    cliente, solicitud_id = _borrador(como)
    _completar(cliente, solicitud_id, pdf_valido)
    assert cliente.post(f"/api/solicitudes/{solicitud_id}/enviar").status_code == 200
    delegacion = como("delegacion.toluca")
    respuesta = delegacion.post(f"/api/recepcion/solicitudes/{solicitud_id}/recibir", json={})
    assert respuesta.status_code == 200
    assert len(respuesta.json()["folio"]) == 5
