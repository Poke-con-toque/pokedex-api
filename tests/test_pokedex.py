"""CRUD de la Pokédex personal."""

import httpx
import pytest
import respx

from app.models import PokedexEntry

POKEDEX = "/api/v1/pokedex"


def anadir(client, headers, pokemon_id, **extra):
    return client.post(POKEDEX, json={"pokemon_id": pokemon_id, **extra}, headers=headers)


@pytest.fixture
def tres_entradas(client, auth_headers, pokeapi):
    """Pikachu capturado, Bulbasaur y Charmander sin capturar (como el comprobador de clase)."""
    return {
        pid: anadir(client, auth_headers, pid, is_captured=capturado).json()
        for pid, capturado in ((25, True), (1, False), (4, False))
    }


@pytest.fixture
def other_user_entry(session, other_user):
    entrada = PokedexEntry(owner_id=other_user.id, pokemon_id=7, pokemon_name="squirtle")
    session.add(entrada)
    session.commit()
    session.refresh(entrada)
    return entrada


# ─────────────────────────── POST ───────────────────────────


def test_add_pokemon_to_pokedex(client, auth_headers, pokeapi):
    respuesta = anadir(client, auth_headers, 25, nickname="Sparky", is_captured=True)
    assert respuesta.status_code == 201
    entrada = respuesta.json()
    assert entrada["pokemon_name"] == "pikachu"
    assert entrada["pokemon_sprite"].endswith("/25.png")
    assert entrada["pokemon_types"] == "electric"
    assert entrada["nickname"] == "Sparky"
    assert entrada["is_captured"] is True
    assert entrada["capture_date"] is not None


def test_add_not_captured_has_no_capture_date(client, auth_headers, pokeapi):
    entrada = anadir(client, auth_headers, 1).json()
    assert entrada["is_captured"] is False
    assert entrada["capture_date"] is None
    assert entrada["pokemon_types"] == "grass,poison"


def test_add_duplicate_pokemon(client, auth_headers, pokeapi):
    anadir(client, auth_headers, 25)
    respuesta = anadir(client, auth_headers, 25)
    assert respuesta.status_code == 409


def test_same_pokemon_for_two_users(client, auth_headers, other_headers, pokeapi):
    assert anadir(client, auth_headers, 25).status_code == 201
    assert anadir(client, other_headers, 25).status_code == 201


def test_add_nonexistent_pokemon(client, auth_headers, pokeapi):
    # 1000 está en el rango válido (1-1025) pero la PokeAPI simulada no lo conoce.
    respuesta = anadir(client, auth_headers, 1000)
    assert respuesta.status_code == 404


def test_add_pokemon_id_out_of_range(client, auth_headers):
    assert anadir(client, auth_headers, 2000).status_code == 422
    assert anadir(client, auth_headers, 0).status_code == 422


@respx.mock
def test_add_when_pokeapi_is_down(client, auth_headers):
    respx.get(url__startswith="https://pokeapi.co").mock(side_effect=httpx.ConnectError("caída"))
    respuesta = anadir(client, auth_headers, 25)
    assert respuesta.status_code == 502


def test_pokedex_requires_token(client):
    assert client.get(POKEDEX).status_code == 401
    assert client.post(POKEDEX, json={"pokemon_id": 25}).status_code == 401


# ─────────────────────────── GET ───────────────────────────


def test_get_pokedex_with_filters(client, auth_headers, tres_entradas):
    capturados = client.get(f"{POKEDEX}?captured=true", headers=auth_headers).json()
    assert [e["pokemon_id"] for e in capturados] == [25]

    no_capturados = client.get(f"{POKEDEX}?captured=false", headers=auth_headers).json()
    assert [e["pokemon_id"] for e in no_capturados] == [1, 4]

    client.patch(f"{POKEDEX}/{tres_entradas[4]['id']}", json={"favorite": True}, headers=auth_headers)
    favoritos = client.get(f"{POKEDEX}?favorite=true", headers=auth_headers).json()
    assert [e["pokemon_id"] for e in favoritos] == [4]


def test_get_pokedex_sorting_and_pagination(client, auth_headers, tres_entradas):
    por_nombre = client.get(f"{POKEDEX}?sort=pokemon_name&order=desc", headers=auth_headers)
    assert [e["pokemon_name"] for e in por_nombre.json()] == ["pikachu", "charmander", "bulbasaur"]

    por_id = client.get(f"{POKEDEX}?sort=pokemon_id&order=asc", headers=auth_headers)
    assert [e["pokemon_id"] for e in por_id.json()] == [1, 4, 25]

    pagina = client.get(f"{POKEDEX}?limit=2&offset=1", headers=auth_headers)
    assert [e["pokemon_id"] for e in pagina.json()] == [4, 25]


def test_get_pokedex_rejects_bad_params(client, auth_headers):
    assert client.get(f"{POKEDEX}?limit=500", headers=auth_headers).status_code == 422
    assert client.get(f"{POKEDEX}?offset=-1", headers=auth_headers).status_code == 422
    assert client.get(f"{POKEDEX}?sort=password", headers=auth_headers).status_code == 422
    assert client.get(f"{POKEDEX}?order=random", headers=auth_headers).status_code == 422


def test_get_pokedex_only_shows_own_entries(client, auth_headers, tres_entradas, other_user_entry):
    ids = [e["pokemon_id"] for e in client.get(POKEDEX, headers=auth_headers).json()]
    assert 7 not in ids


def test_get_entry_detail(client, auth_headers, tres_entradas):
    entrada = tres_entradas[25]
    respuesta = client.get(f"{POKEDEX}/{entrada['id']}", headers=auth_headers)
    assert respuesta.status_code == 200
    assert respuesta.json()["pokemon_name"] == "pikachu"


# ─────────────────────────── PATCH ───────────────────────────


def test_update_pokedex_entry(client, auth_headers, tres_entradas):
    entrada = tres_entradas[1]
    cambios = {
        "is_captured": True,
        "capture_date": "2025-01-13T10:00:00Z",
        "nickname": "Rayo",
        "favorite": True,
    }
    respuesta = client.patch(f"{POKEDEX}/{entrada['id']}", json=cambios, headers=auth_headers)
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["is_captured"] is True
    assert cuerpo["capture_date"].startswith("2025-01-13T10:00:00")
    assert cuerpo["nickname"] == "Rayo"
    assert cuerpo["favorite"] is True


def test_patch_only_changes_sent_fields(client, auth_headers, tres_entradas):
    entrada = tres_entradas[1]
    cuerpo = client.patch(
        f"{POKEDEX}/{entrada['id']}", json={"favorite": True}, headers=auth_headers
    ).json()
    assert cuerpo["favorite"] is True
    assert cuerpo["is_captured"] is False


def test_patch_capture_sets_and_release_clears_date(client, auth_headers, tres_entradas):
    entrada = tres_entradas[4]
    capturado = client.patch(
        f"{POKEDEX}/{entrada['id']}", json={"is_captured": True}, headers=auth_headers
    ).json()
    assert capturado["capture_date"] is not None
    liberado = client.patch(
        f"{POKEDEX}/{entrada['id']}", json={"is_captured": False}, headers=auth_headers
    ).json()
    assert liberado["capture_date"] is None


def test_patch_validates_fields(client, auth_headers, tres_entradas):
    entrada = tres_entradas[25]
    respuesta = client.patch(
        f"{POKEDEX}/{entrada['id']}", json={"nickname": "x" * 51}, headers=auth_headers
    )
    assert respuesta.status_code == 422


def test_cannot_modify_other_user_pokedex(client, auth_headers, other_user_entry):
    ruta = f"{POKEDEX}/{other_user_entry.id}"
    assert client.patch(ruta, json={"favorite": True}, headers=auth_headers).status_code == 404
    assert client.delete(ruta, headers=auth_headers).status_code == 404
    assert client.get(ruta, headers=auth_headers).status_code == 404


# ─────────────────────────── DELETE ───────────────────────────


def test_delete_pokedex_entry(client, auth_headers, tres_entradas):
    ruta = f"{POKEDEX}/{tres_entradas[4]['id']}"
    assert client.delete(ruta, headers=auth_headers).status_code == 204
    assert client.delete(ruta, headers=auth_headers).status_code == 404
    ids = [e["pokemon_id"] for e in client.get(POKEDEX, headers=auth_headers).json()]
    assert ids == [1, 25]


def test_delete_entry_removes_it_from_teams(client, session, auth_headers, tres_entradas, test_user):
    from app.models import Team, TeamMember

    equipo = Team(trainer_id=test_user.id, name="Elite")
    session.add(equipo)
    session.commit()
    session.add(TeamMember(team_id=equipo.id, pokedex_entry_id=tres_entradas[25]["id"], position=1))
    session.commit()

    client.delete(f"{POKEDEX}/{tres_entradas[25]['id']}", headers=auth_headers)
    session.expire_all()
    assert session.get(Team, equipo.id).members == []


# ─────────────────────────── STATS (básico, como en clase) ───────────────────────────


def test_basic_stats(client, auth_headers, tres_entradas):
    client.patch(f"{POKEDEX}/{tres_entradas[1]['id']}", json={"favorite": True}, headers=auth_headers)
    stats = client.get(f"{POKEDEX}/stats", headers=auth_headers).json()
    assert stats["total_pokemon"] == 3
    assert stats["captured"] == 1
    assert stats["favorites"] == 1
    assert stats["completion_percentage"] == 0.1  # 1 de 1025 especies


def test_basic_stats_empty(client, auth_headers):
    stats = client.get(f"{POKEDEX}/stats", headers=auth_headers).json()
    assert stats["total_pokemon"] == 0
    assert stats["completion_percentage"] == 0.0
