"""Búsqueda y detalle de Pokémon (proxy a la PokeAPI simulada)."""

import respx

POKEMON = "/api/v1/pokemon"


def test_search_returns_simplified_list(client, auth_headers, pokeapi):
    respuesta = client.get(f"{POKEMON}/search?limit=3", headers=auth_headers)
    assert respuesta.status_code == 200
    lista = respuesta.json()
    assert [(p["id"], p["name"], p["types"]) for p in lista] == [
        (1, "bulbasaur", ["grass", "poison"]),
        (4, "charmander", ["fire"]),
        (7, "squirtle", ["water"]),
    ]
    assert all(set(p) == {"id", "name", "sprite", "types"} for p in lista)
    assert respuesta.json()[0]["sprite"].endswith("/1.png")


def test_search_pagination(client, auth_headers, pokeapi):
    respuesta = client.get(f"{POKEMON}/search?limit=2&offset=2", headers=auth_headers)
    assert [p["name"] for p in respuesta.json()] == ["squirtle", "pikachu"]


def test_search_by_name_filters(client, auth_headers, pokeapi):
    respuesta = client.get(f"{POKEMON}/search?name=CHAR", headers=auth_headers)
    assert respuesta.status_code == 200
    assert [p["name"] for p in respuesta.json()] == ["charmander"]


def test_search_by_name_partial_and_paginated(client, auth_headers, pokeapi):
    # "r" aparece en bulbasaur, charmander, squirtle y snorlax.
    todos = client.get(f"{POKEMON}/search?name=r", headers=auth_headers).json()
    assert [p["name"] for p in todos] == ["bulbasaur", "charmander", "squirtle", "snorlax"]
    pagina = client.get(f"{POKEMON}/search?name=r&limit=2&offset=1", headers=auth_headers)
    assert [p["name"] for p in pagina.json()] == ["charmander", "squirtle"]


def test_search_by_name_without_results(client, auth_headers, pokeapi):
    respuesta = client.get(f"{POKEMON}/search?name=mewtwo", headers=auth_headers)
    assert respuesta.status_code == 200
    assert respuesta.json() == []


def test_search_validates_params(client, auth_headers):
    for consulta in ("limit=0", "limit=51", "offset=-1", "name=pika%20chu", "name="):
        respuesta = client.get(f"{POKEMON}/search?{consulta}", headers=auth_headers)
        assert respuesta.status_code == 422, consulta


def test_search_requires_token(client):
    assert client.get(f"{POKEMON}/search").status_code == 401


def test_search_uses_cache(client, auth_headers, pokeapi):
    client.get(f"{POKEMON}/search?name=pika", headers=auth_headers)
    client.get(f"{POKEMON}/search?name=pika", headers=auth_headers)
    lista = [r for r in pokeapi.calls if "limit=" in str(r.request.url)]
    assert len(lista) == 1


def test_get_pokemon_detail(client, auth_headers, pokeapi):
    respuesta = client.get(f"{POKEMON}/charmander", headers=auth_headers)
    assert respuesta.status_code == 200
    ficha = respuesta.json()
    assert {"id", "name", "sprite"} <= set(ficha)
    assert ficha["id"] == 4
    assert ficha["types"] == ["fire"]
    assert ficha["stats"] == {"hp": 39, "attack": 52, "defense": 43, "speed": 65}
    assert ficha["abilities"] == ["blaze", "solar-power"]
    assert ficha["sprites"]["front_default"].endswith("/4.png")


def test_get_pokemon_detail_by_id(client, auth_headers, pokeapi):
    assert client.get(f"{POKEMON}/25", headers=auth_headers).json()["name"] == "pikachu"


def test_get_unknown_pokemon_returns_404(client, auth_headers, pokeapi):
    respuesta = client.get(f"{POKEMON}/pikachuu", headers=auth_headers)
    assert respuesta.status_code == 404
    assert "pikachuu" in respuesta.json()["detail"]


def test_get_pokemon_detail_requires_token(client):
    assert client.get(f"{POKEMON}/pikachu").status_code == 401


@respx.mock
def test_get_pokemon_when_pokeapi_times_out(client, auth_headers):
    import httpx

    respx.get(url__startswith="https://pokeapi.co").mock(side_effect=httpx.ReadTimeout("lento"))
    assert client.get(f"{POKEMON}/pikachu", headers=auth_headers).status_code == 504
