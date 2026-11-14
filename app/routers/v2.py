"""Endpoints v2 de la Pokédex: conserva v1 y añade la cadena evolutiva."""

import asyncio
from typing import Literal

from fastapi import APIRouter, Query
from sqlmodel import select

from app.dependencies import CurrentUser, ServicioPokeAPI, SessionDep
from app.models import PokedexEntry, PokedexEntryRead

router = APIRouter(prefix="/pokedex", tags=["pokedex-v2"])
ORDENABLE = {
    "pokemon_id": PokedexEntry.pokemon_id,
    "pokemon_name": PokedexEntry.pokemon_name,
    "capture_date": PokedexEntry.capture_date,
}


class PokedexEntryV2Read(PokedexEntryRead):
    evolution_chain: list[str]


@router.get("", response_model=list[PokedexEntryV2Read])
async def listar_v2(
    usuario: CurrentUser,
    session: SessionDep,
    poke: ServicioPokeAPI,
    captured: bool | None = None,
    favorite: bool | None = None,
    sort: Literal["pokemon_id", "pokemon_name", "capture_date"] = "pokemon_id",
    order: Literal["asc", "desc"] = "asc",
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """Lista la Pokédex como v1 y añade la cadena evolutiva de cada Pokémon.

    v1 sigue disponible durante el ciclo de compatibilidad; cualquier retirada futura
    se anunciará con antelación en la documentación y con cabeceras Deprecation/Sunset.
    """
    consulta = select(PokedexEntry).where(PokedexEntry.owner_id == usuario.id)
    if captured is not None:
        consulta = consulta.where(PokedexEntry.is_captured == captured)
    if favorite is not None:
        consulta = consulta.where(PokedexEntry.favorite == favorite)
    columna = ORDENABLE[sort]
    consulta = consulta.order_by(columna.desc() if order == "desc" else columna.asc())
    entradas = session.exec(consulta.offset(offset).limit(limit)).all()

    async def incluir_evolucion(entrada: PokedexEntry) -> dict:
        especie = await poke.get_pokemon_species(entrada.pokemon_id)
        url = especie.get("evolution_chain_url")
        evolucion = await poke.get_evolution_chain(url) if url else []
        return {**entrada.model_dump(), "evolution_chain": evolucion}

    return await asyncio.gather(*(incluir_evolucion(entrada) for entrada in entradas))
