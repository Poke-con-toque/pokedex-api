"""Pruebas de compatibilidad v1 y evolución en v2."""

from tests.pokeapi_mocks import BASE


def test_v2_pokedex_includes_evolution_chain(client, auth_headers, pokeapi):
    client.post(
        "/api/v1/pokedex",
        json={"pokemon_id": 25},
        headers=auth_headers,
    )
    pokeapi.get(f"{BASE}/pokemon-species/25").respond(
        json={
            "id": 25,
            "name": "pikachu",
            "flavor_text_entries": [],
            "genera": [],
            "evolution_chain": {"url": f"{BASE}/evolution-chain/10/"},
        }
    )
    pokeapi.get(f"{BASE}/evolution-chain/10/").respond(
        json={
            "chain": {
                "species": {"name": "pichu"},
                "evolves_to": [
                    {
                        "species": {"name": "pikachu"},
                        "evolves_to": [{"species": {"name": "raichu"}, "evolves_to": []}],
                    }
                ],
            }
        }
    )

    respuesta = client.get("/api/v2/pokedex", headers=auth_headers)

    assert respuesta.status_code == 200
    assert respuesta.json()[0]["evolution_chain"] == ["pichu", "pikachu", "raichu"]


def test_v1_pokedex_keeps_its_response_shape(client, auth_headers, pokeapi):
    client.post(
        "/api/v1/pokedex",
        json={"pokemon_id": 25},
        headers=auth_headers,
    )
    respuesta = client.get("/api/v1/pokedex", headers=auth_headers)

    assert respuesta.status_code == 200
    assert "evolution_chain" not in respuesta.json()[0]
