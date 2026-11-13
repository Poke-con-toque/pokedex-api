"""Datos de reserva por si la PokeAPI está caída (FAQ del enunciado).

Sólo se usan si POKEAPI_FALLBACK=true. Tienen el mismo formato que devuelve
PokeAPIService.get_pokemon, así que el resto de la API no nota la diferencia.
"""

SPRITES = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon"


def _pokemon(id_, nombre, tipos, hp, ataque, defensa, velocidad, habilidades, alto, peso):
    return {
        "id": id_,
        "name": nombre,
        "sprite": f"{SPRITES}/{id_}.png",
        "types": tipos,
        "stats": {"hp": hp, "attack": ataque, "defense": defensa, "speed": velocidad},
        "abilities": habilidades,
        "sprites": {
            "front_default": f"{SPRITES}/{id_}.png",
            "back_default": f"{SPRITES}/back/{id_}.png",
            "front_shiny": f"{SPRITES}/shiny/{id_}.png",
            "official_artwork": f"{SPRITES}/other/official-artwork/{id_}.png",
        },
        "height": alto,
        "weight": peso,
    }


POKEMON_DE_RESERVA = [
    _pokemon(1, "bulbasaur", ["grass", "poison"], 45, 49, 49, 45, ["overgrow", "chlorophyll"], 7, 69),
    _pokemon(4, "charmander", ["fire"], 39, 52, 43, 65, ["blaze", "solar-power"], 6, 85),
    _pokemon(7, "squirtle", ["water"], 44, 48, 65, 43, ["torrent", "rain-dish"], 5, 90),
    _pokemon(25, "pikachu", ["electric"], 35, 55, 40, 90, ["static", "lightning-rod"], 4, 60),
]
