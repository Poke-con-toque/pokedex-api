"""Pruebas de exportación de fichas Pokémon en PDF."""

from app.services import pdf_service
from tests.pokeapi_mocks import BASE


def mock_especie(pokeapi):
    pokeapi.get(f"{BASE}/pokemon-species/25").respond(
        json={
            "id": 25,
            "name": "pikachu",
            "flavor_text_entries": [],
            "genera": [],
            "evolution_chain": {"url": None},
        }
    )


def test_ficha_devuelve_pdf_y_nombre_de_descarga(client, auth_headers, pokeapi, monkeypatch):
    monkeypatch.setattr(pdf_service, "_descargar_sprite", lambda _url: None)
    mock_especie(pokeapi)

    respuesta = client.get("/api/v1/pokemon/pikachu/card", headers=auth_headers)

    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"] == "application/pdf"
    assert respuesta.headers["content-disposition"] == 'attachment; filename="pikachu.pdf"'
    assert respuesta.content.startswith(b"%PDF")


def test_ficha_pokemon_inexistente_devuelve_404(client, auth_headers, pokeapi):
    respuesta = client.get("/api/v1/pokemon/no-es-un-pokemon/card", headers=auth_headers)
    assert respuesta.status_code == 404


def test_ficha_requiere_autenticacion(client):
    assert client.get("/api/v1/pokemon/pikachu/card").status_code == 401


def test_ficha_se_genera_sin_sprite(client, auth_headers, pokeapi, monkeypatch):
    monkeypatch.setattr(pdf_service, "_descargar_sprite", lambda _url: None)
    mock_especie(pokeapi)
    respuesta = client.get("/api/v1/pokemon/25/card", headers=auth_headers)
    assert respuesta.status_code == 200
    assert respuesta.content.startswith(b"%PDF")
