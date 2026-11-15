"""Proxy de consulta a la PokeAPI: búsqueda, detalle y ficha PDF."""

import asyncio

from fastapi import APIRouter, Query, Request, Response

from app.dependencies import CurrentUser, ServicioPokeAPI
from app.limits import LIMITE_POKEAPI, limiter
from app.models import PokemonDetail, PokemonSummary
from app.services.pdf_service import crear_ficha_pokemon, descargar_sprite

router = APIRouter(prefix="/pokemon", tags=["pokemon"])

# Hay 1025 Pokémon y otras formas por encima del 10000: con 2000 los listamos todos.
TODOS = 2000


def _resumen(ficha: dict) -> dict:
    return {campo: ficha[campo] for campo in ("id", "name", "sprite", "types")}


# /search va ANTES que /{id_or_name}: si no, FastAPI buscaría un Pokémon llamado "search".
@router.get("/search", response_model=list[PokemonSummary])
@limiter.limit(LIMITE_POKEAPI)
async def buscar_pokemon(
    request: Request,
    usuario: CurrentUser,
    poke: ServicioPokeAPI,
    name: str | None = Query(
        default=None,
        min_length=1,
        max_length=50,
        pattern=r"^[A-Za-z0-9-]+$",
        description="Parte del nombre, sin distinguir mayúsculas (p. ej. 'char')",
    ),
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
):
    """Busca Pokémon en la PokeAPI y devuelve una lista simplificada {id, name, sprite, types}."""
    if name:
        # La PokeAPI no busca por texto: pedimos la lista completa (queda en caché),
        # filtramos aquí y paginamos el resultado.
        todos = (await poke.search_pokemon(limit=TODOS, offset=0))["results"]
        texto = name.lower()
        encontrados = [p for p in todos if texto in p["name"]][offset : offset + limit]
    else:
        encontrados = (await poke.search_pokemon(limit=limit, offset=offset))["results"]

    # La lista de la PokeAPI sólo trae nombre y URL: los tipos y el sprite están en la
    # ficha de cada uno. Las pedimos a la vez, no una detrás de otra.
    fichas = await asyncio.gather(*(poke.get_pokemon(p["id"]) for p in encontrados))
    return [_resumen(ficha) for ficha in fichas]


# /{id_or_name}/card también va antes que /{id_or_name}, por el mismo motivo.
@router.get("/{id_or_name}/card")
@limiter.limit(LIMITE_POKEAPI)
async def ficha_pokemon(
    request: Request,
    id_or_name: str, usuario: CurrentUser, poke: ServicioPokeAPI):
    """Descarga una ficha PDF con los datos principales del Pokémon."""
    pokemon = await poke.get_pokemon(id_or_name)
    especie, sprite = await asyncio.gather(
        poke.get_pokemon_species(pokemon["id"]), descargar_sprite(pokemon["sprite"])
    )
    contenido = crear_ficha_pokemon(pokemon, especie.get("description"), sprite)
    return Response(
        content=contenido,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{pokemon["name"]}.pdf"'},
    )


@router.get("/{id_or_name}", response_model=PokemonDetail)
@limiter.limit(LIMITE_POKEAPI)
async def consultar_pokemon(
    request: Request,
    id_or_name: str, usuario: CurrentUser, poke: ServicioPokeAPI):
    """Detalle de un Pokémon: stats, habilidades, tipos y sprites."""
    return await poke.get_pokemon(id_or_name)
