"""Proxy de consulta a la PokeAPI: búsqueda, detalle y ficha PDF."""

import asyncio

from fastapi import APIRouter, Query, Response

from app.dependencies import CurrentUser, ServicioPokeAPI
from app.models import PokemonDetail, PokemonSummary
from app.services.pdf_service import crear_ficha_pokemon

router = APIRouter(prefix="/pokemon", tags=["pokemon"])

# Hay 1025 Pokémon y otras formas por encima del 10000: con 2000 los listamos todos.
TODOS = 2000


def _resumen(ficha: dict) -> dict:
    return {campo: ficha[campo] for campo in ("id", "name", "sprite", "types")}


@router.get("/search", response_model=list[PokemonSummary])
async def buscar_pokemon(
    usuario: CurrentUser,
    poke: ServicioPokeAPI,
    name: str | None = Query(default=None, min_length=1, max_length=50, pattern=r"^[A-Za-z0-9-]+$"),
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
):
    """Busca Pokémon y devuelve una lista simplificada."""
    if name:
        todos = (await poke.search_pokemon(limit=TODOS, offset=0))["results"]
        texto = name.lower()
        encontrados = [p for p in todos if texto in p["name"]][offset : offset + limit]
    else:
        encontrados = (await poke.search_pokemon(limit=limit, offset=offset))["results"]

    fichas = await asyncio.gather(*(poke.get_pokemon(p["id"]) for p in encontrados))
    return [_resumen(ficha) for ficha in fichas]


@router.get("/{id_or_name}/card")
async def ficha_pokemon(id_or_name: str, usuario: CurrentUser, poke: ServicioPokeAPI):
    """Descarga una ficha PDF con los datos principales del Pokémon."""
    pokemon = await poke.get_pokemon(id_or_name)
    especie = await poke.get_pokemon_species(pokemon["id"])
    contenido = crear_ficha_pokemon(pokemon, especie.get("description"))
    return Response(
        content=contenido,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{pokemon["name"]}.pdf"'},
    )


@router.get("/{id_or_name}", response_model=PokemonDetail)
async def consultar_pokemon(id_or_name: str, usuario: CurrentUser, poke: ServicioPokeAPI):
    """Detalle de un Pokémon: stats, habilidades, tipos y sprites."""
    return await poke.get_pokemon(id_or_name)
