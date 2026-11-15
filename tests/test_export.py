"""Exportación de la Pokédex a CSV y PDF."""

import csv
import io

from app.models import PokedexEntry, ahora

EXPORT = "/api/v1/pokedex/export"


def leer_csv(respuesta) -> list[dict]:
    texto = respuesta.content.decode("utf-8-sig")  # quita el BOM
    return list(csv.DictReader(io.StringIO(texto)))


def poblar(session, usuario):
    for pid, nombre, tipos, capturado, favorito, mote in (
        (25, "pikachu", "electric", True, True, "Sparky"),
        (1, "bulbasaur", "grass,poison", False, False, None),
        (4, "charmander", "fire", True, False, "Ñoño “Fuego”"),
    ):
        session.add(
            PokedexEntry(
                owner_id=usuario.id,
                pokemon_id=pid,
                pokemon_name=nombre,
                pokemon_types=tipos,
                is_captured=capturado,
                capture_date=ahora() if capturado else None,
                favorite=favorito,
                nickname=mote,
            )
        )
    session.commit()


def test_export_csv(client, session, auth_headers, test_user):
    poblar(session, test_user)
    respuesta = client.get(f"{EXPORT}?format=csv", headers=auth_headers)
    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"].startswith("text/csv")
    assert respuesta.headers["content-disposition"] == 'attachment; filename="pokedex.csv"'
    filas = leer_csv(respuesta)
    assert list(filas[0]) == [
        "pokemon_id", "pokemon_name", "nickname", "types",
        "is_captured", "capture_date", "favorite", "notes",
    ]
    assert [f["pokemon_id"] for f in filas] == ["1", "4", "25"]
    assert filas[0]["types"] == "grass,poison"
    assert filas[1]["nickname"] == "Ñoño “Fuego”"  # UTF-8 completo en el CSV


def test_export_csv_is_default_format(client, session, auth_headers, test_user):
    poblar(session, test_user)
    respuesta = client.get(EXPORT, headers=auth_headers)
    assert respuesta.headers["content-disposition"].endswith('"pokedex.csv"')


def test_export_csv_with_filters(client, session, auth_headers, test_user):
    poblar(session, test_user)
    capturados = leer_csv(client.get(f"{EXPORT}?captured=true", headers=auth_headers))
    assert [f["pokemon_name"] for f in capturados] == ["charmander", "pikachu"]
    favoritos = leer_csv(
        client.get(f"{EXPORT}?captured=true&favorite=true", headers=auth_headers)
    )
    assert [f["pokemon_name"] for f in favoritos] == ["pikachu"]


def test_export_csv_prevents_formula_injection(client, session, auth_headers, test_user):
    session.add(
        PokedexEntry(
            owner_id=test_user.id,
            pokemon_id=25,
            pokemon_name="pikachu",
            nickname="=HYPERLINK(\"http://malo\")",
                notes=" =SUM(A1)"
        )
    )
    session.commit()
    fila = leer_csv(client.get(EXPORT, headers=auth_headers))[0]
    assert fila["nickname"].startswith("'=")
    assert fila["notes"] == "' =SUM(A1)"


def test_export_pdf(client, session, auth_headers, test_user):
    poblar(session, test_user)
    respuesta = client.get(f"{EXPORT}?format=pdf&favorite=true", headers=auth_headers)
    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"] == "application/pdf"
    assert respuesta.headers["content-disposition"] == 'attachment; filename="pokedex.pdf"'
    assert respuesta.content.startswith(b"%PDF")


def test_export_pdf_empty_pokedex(client, auth_headers):
    respuesta = client.get(f"{EXPORT}?format=pdf&captured=false", headers=auth_headers)
    assert respuesta.status_code == 200
    assert respuesta.content.startswith(b"%PDF")


def test_export_invalid_format(client, auth_headers):
    assert client.get(f"{EXPORT}?format=xlsx", headers=auth_headers).status_code == 422


def test_export_only_own_entries(client, session, auth_headers, other_user):
    poblar(session, other_user)
    assert leer_csv(client.get(EXPORT, headers=auth_headers)) == []


def test_export_requires_token(client):
    assert client.get(EXPORT).status_code == 401
