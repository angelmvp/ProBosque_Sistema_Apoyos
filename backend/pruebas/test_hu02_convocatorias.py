"""HU-02 Consulta de convocatorias con filtros de región/municipio y visor de PDF único.

HU-02-CA-1: un programa con convocatoria vigente muestra su PDF y la delegación del municipio elegido.
HU-02-CA-2: un programa sin convocatoria vigente no se muestra como abierto y avisa que no hay convocatoria abierta.
"""


def test_ca1_programa_vigente_muestra_pdf_y_delegacion(cliente, publicar):
    pub = publicar("capturando_carbono")
    municipios = cliente.get("/api/publico/municipios").json()
    metepec = next(m for m in municipios if m["nombre"] == "Metepec")
    d = cliente.get(f"/api/publico/programas/capturando_carbono?municipio_id={metepec['id']}").json()
    assert d["estado"] == "vigente" and d["convocatoria_abierta"] is True
    assert d["publicacion"]["url_pdf"] == f"/api/publico/publicaciones/{pub['id']}/pdf"
    assert d["delegacion"]["nombre"].startswith("Región I")
    pdf = cliente.get(d["publicacion"]["url_pdf"])
    assert pdf.status_code == 200 and pdf.headers["content-type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF")


def test_ca2_sin_convocatoria_no_aparece_abierto(cliente, publicar):
    publicar("capturando_carbono")
    d = cliente.get("/api/publico/programas/guardabosques").json()
    assert d["estado"] == "sin_convocatoria" and d["convocatoria_abierta"] is False
    assert d["publicacion"] is None
    abiertos = cliente.get("/api/publico/programas?estado=vigente").json()
    assert [p["clave"] for p in abiertos] == ["capturando_carbono"]


def test_ca2_convocatoria_vencida_es_historica_y_no_abierta(cliente, publicar):
    publicar("servicios_ambientales_hidrologicos", desde=-100, hasta=-10)
    d = cliente.get("/api/publico/programas/servicios_ambientales_hidrologicos").json()
    assert d["estado"] == "historica" and d["convocatoria_abierta"] is False


def test_filtro_por_nombre_de_programa(cliente):
    r = cliente.get("/api/publico/programas?q=carbono").json()
    assert [p["clave"] for p in r] == ["capturando_carbono"]


def test_regiones_y_municipios_del_catalogo(cliente):
    regiones = cliente.get("/api/publico/regiones").json()
    assert len(regiones) == 9
    r1 = next(r for r in regiones if r["clave"] == "I")
    municipios = cliente.get(f"/api/publico/municipios?region_id={r1['id']}").json()
    assert {"Toluca", "Metepec", "Huixquilucan"} <= {m["nombre"] for m in municipios}


def test_formatos_descargables_por_programa(cliente):
    d = cliente.get("/api/publico/programas/capturando_carbono").json()
    claves = {f["clave"] for f in d["formatos"]}
    assert claves and all(cliente.get(f"/api/publico/formatos/{c}").status_code == 200 for c in claves)


def test_borrador_no_es_publico(cliente, publicar):
    borrador = publicar(accion="borrador")
    assert cliente.get(f"/api/publico/publicaciones/{borrador['id']}/pdf").status_code == 404
    d = cliente.get("/api/publico/programas/capturando_carbono").json()
    assert d["estado"] == "sin_convocatoria"
