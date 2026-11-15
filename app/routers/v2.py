"""Endpoints v2 de la Pokédex: conserva v1 y añade la cadena evolutiva."""

import asyncio

from fastapi import APIRouter

from app.dependencies import CurrentUser, ServicioPokeAPI, SessionDep
from app.models import PokedexEntry, PokedexEntryV2Read
from app.routers.pokedex import Filtros, entradas_filtradas

router = APIRouter(prefix="/pokedex", tags=["pokedex-v2"])


@router.get("", response_model=list[PokedexEntryV2Read])
async def listar_v2(
    usuario: CurrentUser,
    session: SessionDep,
    poke: ServicioPokeAPI,
    filtros: Filtros,
):
    """Lista la Pokédex como v1 y añade la cadena evolutiva de cada Pokémon.

    Usa los mismos filtros, orden y paginación que v1 (no se duplica la consulta).
    v1 sigue disponible durante el ciclo de compatibilidad; cualquier retirada futura
    se anunciará con antelación en la documentación y con cabeceras Deprecation/Sunset.
    """
    entradas = entradas_filtradas(session, usuario.id, filtros)

    async def incluir_evolucion(entrada: PokedexEntry) -> dict:
        especie = await poke.get_pokemon_species(entrada.pokemon_id)
        url = especie.get("evolution_chain_url")
        evolucion = await poke.get_evolution_chain(url) if url else []
        return {**entrada.model_dump(), "evolution_chain": evolucion}

    # Las especies y cadenas evolutivas se piden en paralelo (y quedan en caché).
    return await asyncio.gather(*(incluir_evolucion(entrada) for entrada in entradas))
