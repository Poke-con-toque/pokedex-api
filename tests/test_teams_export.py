"""Pruebas de exportación de equipos y estadísticas combinadas."""

from app.models import Team
from app.services import pdf_service
from app.services.pdf_service import calcular_estadisticas_equipo


def test_estadisticas_combinadas_suman_y_promedian():
    datos = [
        {"stats": {"hp": 40, "attack": 50, "defense": 30, "speed": 60}, "types": ["electric"]},
        {"stats": {"hp": 80, "attack": 70, "defense": 50, "speed": 40}, "types": ["water", "ice"]},
    ]

    resultado = calcular_estadisticas_equipo(datos)

    assert resultado["sum"] == {"hp": 120, "attack": 120, "defense": 80, "speed": 100}
    assert resultado["average"] == {"hp": 60.0, "attack": 60.0, "defense": 40.0, "speed": 50.0}
    assert resultado["types"] == ["electric", "ice", "water"]


def test_exportar_equipo_devuelve_pdf(client, auth_headers, pokeapi, monkeypatch):
    monkeypatch.setattr(pdf_service, "_descargar_sprite", lambda _url: None)
    client.post("/api/v1/pokedex", json={"pokemon_id": 25}, headers=auth_headers)
    equipo = client.post(
        "/api/v1/teams",
        json={"name": "Kanto", "description": "Mi equipo", "pokemon_ids": [25]},
        headers=auth_headers,
    ).json()

    respuesta = client.get(f"/api/v1/teams/{equipo['id']}/export", headers=auth_headers)

    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"] == "application/pdf"
    assert respuesta.headers["content-disposition"] == 'attachment; filename="equipo-kanto.pdf"'
    assert respuesta.content.startswith(b"%PDF")


def test_no_exportar_equipo_ajeno(client, session, auth_headers, other_user):
    equipo = Team(trainer_id=other_user.id, name="Ajeno")
    session.add(equipo)
    session.commit()

    respuesta = client.get(f"/api/v1/teams/{equipo.id}/export", headers=auth_headers)
    assert respuesta.status_code == 404
