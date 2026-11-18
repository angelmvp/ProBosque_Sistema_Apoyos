"""HU-03 Gestión de publicaciones (Dirección General de PROBOSQUE).

HU-03-CA-1: al publicar una convocatoria vigente, el portal la muestra en el programa correspondiente.
HU-03-CA-2: lo ya publicado no se puede despublicar ni modificar; solo los borradores se editan o eliminan.
"""
import io
from datetime import date, timedelta


def test_ca1_publicar_aparece_en_el_portal(cliente, publicar):
    antes = cliente.get("/api/publico/programas/plantaciones_sustentables").json()
    assert antes["convocatoria_abierta"] is False
    publicar("plantaciones_sustentables", titulo="Plantaciones 2026")
    despues = cliente.get("/api/publico/programas/plantaciones_sustentables").json()
    assert despues["convocatoria_abierta"] is True
    assert despues["publicacion"]["titulo"] == "Plantaciones 2026"


def test_ca2_lo_publicado_no_se_modifica_ni_se_elimina(como, publicar, pdf_valido):
    director = como("direccion.general")
    pub = publicar()
    hoy = date.today()
    datos = {"programa": "capturando_carbono", "titulo": "Otro", "accion": "borrador",
             "vigencia_inicio": hoy.isoformat(), "vigencia_fin": (hoy + timedelta(days=5)).isoformat()}
    assert director.put(f"/api/publicaciones/{pub['id']}", data=datos).status_code == 409
    assert director.delete(f"/api/publicaciones/{pub['id']}").status_code == 409
    assert director.post(f"/api/publicaciones/{pub['id']}/publicar").status_code == 409
    assert director.get(f"/api/publicaciones/{pub['id']}").json()["titulo"] == pub["titulo"]


def test_ca2_el_borrador_si_se_edita_y_se_elimina(como, publicar):
    director = como("direccion.general")
    borrador = publicar(accion="borrador", titulo="Borrador")
    assert borrador["estado"] == "borrador"
    hoy = date.today()
    r = director.put(f"/api/publicaciones/{borrador['id']}", data={
        "programa": "capturando_carbono", "titulo": "Editado", "accion": "borrador",
        "vigencia_inicio": hoy.isoformat(), "vigencia_fin": (hoy + timedelta(days=10)).isoformat()})
    assert r.status_code == 200 and r.json()["titulo"] == "Editado"
    assert director.delete(f"/api/publicaciones/{borrador['id']}").status_code == 204
    assert director.get(f"/api/publicaciones/{borrador['id']}").status_code == 404


def test_publicar_un_borrador(como, publicar):
    director = como("direccion.general")
    b = publicar(accion="borrador")
    r = director.post(f"/api/publicaciones/{b['id']}/publicar")
    assert r.status_code == 200 and r.json()["estado"] == "vigente"


def test_validaciones(como, pdf_valido):
    director = como("direccion.general")
    hoy = date.today()

    def enviar(archivo, titulo="T", inicio=hoy, fin=hoy + timedelta(days=3), accion="publicar"):
        files = {"archivo": archivo} if archivo else None
        return director.post("/api/publicaciones", data={
            "programa": "capturando_carbono", "titulo": titulo, "accion": accion,
            "vigencia_inicio": inicio.isoformat(), "vigencia_fin": fin.isoformat()}, files=files)

    assert enviar(None).status_code == 422                                              # publicar sin PDF
    assert enviar(("a.pdf", io.BytesIO(b"no soy pdf"), "application/pdf")).status_code == 422
    assert enviar(("a.pdf", io.BytesIO(b""), "application/pdf")).status_code == 422
    ok = ("a.pdf", io.BytesIO(pdf_valido), "application/pdf")
    assert enviar(ok, titulo="  ").status_code == 422
    assert enviar(("a.pdf", io.BytesIO(pdf_valido), "application/pdf"), inicio=hoy, fin=hoy - timedelta(days=1)).status_code == 422
    assert enviar(None, accion="borrador").status_code == 201                            # borrador sin PDF sí


def test_la_publicacion_queda_en_bitacora(como, publicar):
    from sqlalchemy import select
    from app.nucleo import base_datos
    from app.servicios.bitacora.modelos import Bitacora
    publicar()
    s = base_datos.nueva_sesion()
    acciones = [b.accion for b in s.scalars(select(Bitacora))]
    s.close()
    assert any("publica" in a for a in acciones)
