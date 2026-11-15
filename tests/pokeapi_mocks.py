"""Respuestas de ejemplo de la PokeAPI, con su formato real, para simularla en los tests."""

BASE = "https://pokeapi.co/api/v2"
SPRITES = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon"

# Imagen PNG válida de 1x1 píxeles, para simular la descarga de sprites.
PNG_1X1 = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02"
    b"\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x03\x01"
    b"\x01\x00\xc9\xfe\x92\xef\x00\x00\x00\x00IEND\xaeB`\x82"
)

DATOS = {
    1: ("bulbasaur", ["grass", "poison"], (45, 49, 49, 65, 65, 45), ["overgrow", "chlorophyll"]),
    4: ("charmander", ["fire"], (39, 52, 43, 60, 50, 65), ["blaze", "solar-power"]),
    7: ("squirtle", ["water"], (44, 48, 65, 50, 64, 43), ["torrent", "rain-dish"]),
    25: ("pikachu", ["electric"], (35, 55, 40, 50, 50, 90), ["static", "lightning-rod"]),
    133: ("eevee", ["normal"], (55, 55, 50, 45, 65, 55), ["run-away", "adaptability"]),
    143: ("snorlax", ["normal"], (160, 110, 65, 65, 110, 30), ["immunity", "thick-fat"]),
}
NOMBRES_STATS = ("hp", "attack", "defense", "special-attack", "special-defense", "speed")


def pokemon_bruto(pokemon_id: int) -> dict:
    nombre, tipos, stats, habilidades = DATOS[pokemon_id]
    return {
        "id": pokemon_id,
        "name": nombre,
        "height": 7,
        "weight": 69,
        "sprites": {
            "front_default": f"{SPRITES}/{pokemon_id}.png",
            "back_default": f"{SPRITES}/back/{pokemon_id}.png",
            "front_shiny": f"{SPRITES}/shiny/{pokemon_id}.png",
            "other": {
                "official-artwork": {
                    "front_default": f"{SPRITES}/other/official-artwork/{pokemon_id}.png"
                }
            },
        },
        "types": [
            {"slot": i + 1, "type": {"name": t, "url": f"{BASE}/type/{t}/"}}
            for i, t in enumerate(tipos)
        ],
        "stats": [
            {"base_stat": valor, "effort": 0, "stat": {"name": n, "url": ""}}
            for n, valor in zip(NOMBRES_STATS, stats, strict=True)
        ],
        "abilities": [
            {"ability": {"name": h, "url": ""}, "is_hidden": False, "slot": i + 1}
            for i, h in enumerate(habilidades)
        ],
    }


def lista_bruta(limit: int = 20, offset: int = 0) -> dict:
    ids = sorted(DATOS)[offset : offset + limit]
    return {
        "count": 1025,
        "next": None,
        "previous": None,
        "results": [
            {"name": DATOS[i][0], "url": f"{BASE}/pokemon/{i}/"} for i in ids
        ],
    }


def tipo_bruto(tipo: str) -> dict:
    return {
        "id": 1,
        "name": tipo,
        "pokemon": [
            {"pokemon": {"name": d[0], "url": f"{BASE}/pokemon/{i}/"}, "slot": 1}
            for i, d in DATOS.items()
            if tipo in d[1]
        ],
    }


def especie_bruta(pokemon_id: int) -> dict:
    nombre = DATOS[pokemon_id][0]
    return {
        "id": pokemon_id,
        "name": nombre,
        "flavor_text_entries": [
            {
                "flavor_text": "When several of\nthese POKéMON gather,\fthey cause storms.",
                "language": {"name": "en", "url": ""},
                "version": {"name": "red", "url": ""},
            },
            {
                "flavor_text": f"Descripción\nde {nombre}\fen español.",
                "language": {"name": "es", "url": ""},
                "version": {"name": "x", "url": ""},
            },
        ],
        "genera": [
            {"genus": "Mouse Pokémon", "language": {"name": "en", "url": ""}},
            {"genus": "Pokémon Ratón", "language": {"name": "es", "url": ""}},
        ],
        "evolution_chain": {"url": f"{BASE}/evolution-chain/10/"},
    }


def cadena_evolutiva_bruta() -> dict:
    return {
        "id": 10,
        "chain": {
            "species": {"name": "pichu", "url": ""},
            "evolves_to": [
                {
                    "species": {"name": "pikachu", "url": ""},
                    "evolves_to": [
                        {"species": {"name": "raichu", "url": ""}, "evolves_to": []}
                    ],
                }
            ],
        },
    }
