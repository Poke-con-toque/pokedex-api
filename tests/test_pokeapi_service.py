"""Cliente de la PokeAPI, con la PokeAPI simulada por respx (los tests no salen a Internet)."""

import logging

import httpx
import pytest
import respx
from fastapi import HTTPException

from app.dependencies import get_pokeapi_service
from app.services.pokeapi_service import PokeAPIService
from tests.pokeapi_mocks import (
    BASE,
    cadena_evolutiva_bruta,
    especie_bruta,
    lista_bruta,
    pokemon_bruto,
    tipo_bruto,
)


@pytest.fixture
def servicio():
    return PokeAPIService(BASE)


@pytest.mark.asyncio
@respx.mock
async def test_pokeapi_service_get_pokemon(servicio):
    respx.get(f"{BASE}/pokemon/25").respond(json=pokemon_bruto(25))
    pikachu = await servicio.get_pokemon(25)
    assert pikachu["id"] == 25
    assert pikachu["name"] == "pikachu"
    assert pikachu["types"] == ["electric"]
    assert pikachu["stats"] == {"hp": 35, "attack": 55, "defense": 40, "speed": 90}
    assert pikachu["abilities"] == ["static", "lightning-rod"]
    assert pikachu["sprite"].endswith("/25.png")
    assert pikachu["sprites"]["official_artwork"].endswith("/official-artwork/25.png")


@pytest.mark.asyncio
@respx.mock
async def test_pokeapi_service_get_pokemon_by_name_is_case_insensitive(servicio):
    ruta = respx.get(f"{BASE}/pokemon/pikachu").respond(json=pokemon_bruto(25))
    assert (await servicio.get_pokemon(" Pikachu "))["id"] == 25
    assert ruta.called


@pytest.mark.asyncio
@respx.mock
async def test_pokeapi_service_handles_404(servicio):
    respx.get(f"{BASE}/pokemon/pikachuu").respond(404)
    with pytest.raises(HTTPException) as error:
        await servicio.get_pokemon("pikachuu")
    assert error.value.status_code == 404
    assert "pikachuu" in error.value.detail


@pytest.mark.asyncio
@respx.mock
async def test_pokeapi_service_handles_timeout(servicio):
    respx.get(f"{BASE}/pokemon/25").mock(side_effect=httpx.ReadTimeout("lento"))
    with pytest.raises(HTTPException) as error:
        await servicio.get_pokemon(25)
    assert error.value.status_code == 504


@pytest.mark.asyncio
@respx.mock
async def test_pokeapi_service_handles_connection_error(servicio):
    respx.get(f"{BASE}/pokemon/25").mock(side_effect=httpx.ConnectError("sin red"))
    with pytest.raises(HTTPException) as error:
        await servicio.get_pokemon(25)
    assert error.value.status_code == 502


@pytest.mark.asyncio
@respx.mock
async def test_pokeapi_service_handles_500(servicio):
    respx.get(f"{BASE}/pokemon/25").respond(500)
    with pytest.raises(HTTPException) as error:
        await servicio.get_pokemon(25)
    assert error.value.status_code == 502


@pytest.mark.asyncio
async def test_pokeapi_service_rejects_invalid_identifiers(servicio):
    for malo in (0, "000", "pika chu", "<script>", "a" * 51):
        with pytest.raises(HTTPException) as error:
            await servicio.get_pokemon(malo)
        assert error.value.status_code == 422


@pytest.mark.asyncio
@respx.mock
async def test_pokeapi_service_uses_cache(servicio):
    ruta = respx.get(f"{BASE}/pokemon/25").respond(json=pokemon_bruto(25))
    await servicio.get_pokemon(25)
    await PokeAPIService(BASE).get_pokemon(25)  # otra instancia, misma caché
    assert ruta.call_count == 1


@pytest.mark.asyncio
@respx.mock
async def test_pokeapi_service_logs_requests(servicio, caplog):
    respx.get(f"{BASE}/pokemon/25").respond(json=pokemon_bruto(25))
    with caplog.at_level(logging.INFO, logger="pokedex_api.pokeapi"):
        await servicio.get_pokemon(25)
    assert f"{BASE}/pokemon/25 → 200" in caplog.text


@pytest.mark.asyncio
@respx.mock
async def test_pokeapi_service_search(servicio):
    respx.get(f"{BASE}/pokemon?limit=3&offset=0").respond(json=lista_bruta(3))
    pagina = await servicio.search_pokemon(limit=3, offset=0)
    assert pagina["count"] == 1025
    assert pagina["results"] == [
        {"id": 1, "name": "bulbasaur"},
        {"id": 4, "name": "charmander"},
        {"id": 7, "name": "squirtle"},
    ]


@pytest.mark.asyncio
async def test_pokeapi_service_search_validates_params(servicio):
    for limit, offset in ((0, 0), (2001, 0), (20, -1)):
        with pytest.raises(HTTPException) as error:
            await servicio.search_pokemon(limit=limit, offset=offset)
        assert error.value.status_code == 422


@pytest.mark.asyncio
@respx.mock
async def test_pokeapi_service_by_type(servicio):
    respx.get(f"{BASE}/type/normal").respond(json=tipo_bruto("normal"))
    normales = await servicio.get_pokemon_by_type("normal")
    assert normales == [{"id": 133, "name": "eevee"}, {"id": 143, "name": "snorlax"}]


@pytest.mark.asyncio
@respx.mock
async def test_pokeapi_service_by_unknown_type(servicio):
    respx.get(f"{BASE}/type/sonido").respond(404)
    with pytest.raises(HTTPException) as error:
        await servicio.get_pokemon_by_type("sonido")
    assert error.value.status_code == 404


@pytest.mark.asyncio
@respx.mock
async def test_pokeapi_service_species_prefers_spanish(servicio):
    respx.get(f"{BASE}/pokemon-species/25").respond(json=especie_bruta(25))
    especie = await servicio.get_pokemon_species(25)
    assert especie["description"] == "Descripción de pikachu en español."
    assert especie["genus"] == "Pokémon Ratón"
    assert especie["evolution_chain_url"] == f"{BASE}/evolution-chain/10/"


@pytest.mark.asyncio
@respx.mock
async def test_pokeapi_service_species_falls_back_to_english(servicio):
    bruta = especie_bruta(25)
    bruta["flavor_text_entries"] = bruta["flavor_text_entries"][:1]
    bruta["genera"] = []
    respx.get(f"{BASE}/pokemon-species/25").respond(json=bruta)
    especie = await servicio.get_pokemon_species(25)
    assert especie["description"] == "When several of these POKéMON gather, they cause storms."
    assert especie["genus"] is None


@pytest.mark.asyncio
@respx.mock
async def test_pokeapi_service_evolution_chain(servicio):
    respx.get(f"{BASE}/evolution-chain/10/").respond(json=cadena_evolutiva_bruta())
    cadena = await servicio.get_evolution_chain(f"{BASE}/evolution-chain/10/")
    assert cadena == ["pichu", "pikachu", "raichu"]


@pytest.mark.asyncio
@respx.mock
async def test_pokeapi_service_fallback_when_down():
    respx.get(f"{BASE}/pokemon/pikachu").mock(side_effect=httpx.ConnectError("caída"))
    respx.get(f"{BASE}/pokemon/150").mock(side_effect=httpx.ConnectError("caída"))
    servicio = PokeAPIService(BASE, usar_reserva=True)
    assert (await servicio.get_pokemon("pikachu"))["id"] == 25
    with pytest.raises(HTTPException) as error:  # Mewtwo no está en la reserva
        await servicio.get_pokemon(150)
    assert error.value.status_code == 502


@pytest.mark.asyncio
@respx.mock
async def test_pokeapi_service_cache_is_bounded(servicio, monkeypatch):
    from app.services import pokeapi_service

    monkeypatch.setattr(pokeapi_service, "CACHE_MAX", 2)
    for pid in (1, 4, 7):
        respx.get(f"{BASE}/pokemon/{pid}").respond(json=pokemon_bruto(pid))
        await servicio.get_pokemon(pid)
    assert len(pokeapi_service._cache) == 2
    assert f"{BASE}/pokemon/1" not in pokeapi_service._cache


def test_get_pokeapi_service_uses_settings():
    servicio = get_pokeapi_service()
    assert servicio.base_url == "https://pokeapi.co/api/v2"
    assert servicio.timeout == 5.0
