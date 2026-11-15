"""Gestión de equipos de batalla propiedad de cada usuario."""

import asyncio
import re

from fastapi import APIRouter, HTTPException, Response, status
from sqlmodel import select

from app.dependencies import CurrentUser, ServicioPokeAPI, SessionDep
from app.models import (
    PokedexEntry,
    Team,
    TeamCreate,
    TeamMember,
    TeamMemberRead,
    TeamRead,
)
from app.services.pdf_service import crear_pdf_equipo, descargar_sprites

router = APIRouter(prefix="/teams", tags=["teams"])


def _equipo_propio(session: SessionDep, team_id: int, usuario: CurrentUser) -> Team:
    equipo = session.get(Team, team_id)
    if equipo is None or equipo.trainer_id != usuario.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No existe ese equipo")
    return equipo


def _entradas_de_usuario(session: SessionDep, usuario: CurrentUser, pokemon_ids: list[int]):
    if not pokemon_ids:
        return {}
    entradas = session.exec(
        select(PokedexEntry).where(
            PokedexEntry.owner_id == usuario.id,
            PokedexEntry.pokemon_id.in_(pokemon_ids),
        )
    ).all()
    por_id = {entrada.pokemon_id: entrada for entrada in entradas}
    faltan = [pokemon_id for pokemon_id in pokemon_ids if pokemon_id not in por_id]
    if faltan:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"Estos Pokémon no están en tu Pokédex: {faltan}",
        )
    return por_id


def _serializar(session: SessionDep, equipo: Team) -> TeamRead:
    miembros = session.exec(
        select(TeamMember)
        .where(TeamMember.team_id == equipo.id)
        .order_by(TeamMember.position)
    ).all()
    salida = []
    for miembro in miembros:
        entrada = session.get(PokedexEntry, miembro.pokedex_entry_id)
        if entrada is not None:
            salida.append(
                TeamMemberRead(
                    pokemon_id=entrada.pokemon_id,
                    pokemon_name=entrada.pokemon_name,
                    pokemon_sprite=entrada.pokemon_sprite,
                    position=miembro.position,
                )
            )
    return TeamRead(
        id=equipo.id,
        name=equipo.name,
        description=equipo.description,
        created_at=equipo.created_at,
        members=salida,
    )


def _crear_miembros(session: SessionDep, equipo: Team, entradas: dict[int, PokedexEntry], ids: list[int]):
    for posicion, pokemon_id in enumerate(ids, start=1):
        session.add(
            TeamMember(
                team_id=equipo.id,
                pokedex_entry_id=entradas[pokemon_id].id,
                position=posicion,
            )
        )


@router.post("", response_model=TeamRead, status_code=status.HTTP_201_CREATED)
def crear(datos: TeamCreate, usuario: CurrentUser, session: SessionDep):
    entradas = _entradas_de_usuario(session, usuario, datos.pokemon_ids)
    equipo = Team(
        trainer_id=usuario.id,
        name=datos.name,
        description=datos.description,
    )
    session.add(equipo)
    session.flush()
    _crear_miembros(session, equipo, entradas, datos.pokemon_ids)
    session.commit()
    session.refresh(equipo)
    return _serializar(session, equipo)


@router.get("", response_model=list[TeamRead])
def listar(usuario: CurrentUser, session: SessionDep):
    equipos = session.exec(
        select(Team).where(Team.trainer_id == usuario.id).order_by(Team.id)
    ).all()
    return [_serializar(session, equipo) for equipo in equipos]


@router.get("/{team_id}", response_model=TeamRead)
def detalle(team_id: int, usuario: CurrentUser, session: SessionDep):
    return _serializar(session, _equipo_propio(session, team_id, usuario))


@router.put("/{team_id}", response_model=TeamRead)
def actualizar(team_id: int, datos: TeamCreate, usuario: CurrentUser, session: SessionDep):
    equipo = _equipo_propio(session, team_id, usuario)
    entradas = _entradas_de_usuario(session, usuario, datos.pokemon_ids)
    equipo.name = datos.name
    equipo.description = datos.description
    for miembro in session.exec(select(TeamMember).where(TeamMember.team_id == equipo.id)):
        session.delete(miembro)
    session.flush()
    _crear_miembros(session, equipo, entradas, datos.pokemon_ids)
    session.add(equipo)
    session.commit()
    session.refresh(equipo)
    return _serializar(session, equipo)


@router.get("/{team_id}/export")
async def exportar_equipo(
    team_id: int,
    usuario: CurrentUser,
    session: SessionDep,
    poke: ServicioPokeAPI,
):
    equipo = _equipo_propio(session, team_id, usuario)
    miembros = session.exec(
        select(TeamMember)
        .where(TeamMember.team_id == equipo.id)
        .order_by(TeamMember.position)
    ).all()
    entradas = [
        session.get(PokedexEntry, miembro.pokedex_entry_id)
        for miembro in miembros
    ]
    # Fichas y sprites se piden en paralelo: con 6 Pokémon, uno detrás de otro tardaría 6 veces más.
    pokemon = await asyncio.gather(
        *(poke.get_pokemon(entrada.pokemon_id) for entrada in entradas if entrada is not None)
    )
    sprites = await descargar_sprites([ficha["sprite"] for ficha in pokemon])
    contenido = crear_pdf_equipo(equipo.name, equipo.description, list(pokemon), sprites)
    nombre_archivo = re.sub(r"[^a-zA-Z0-9_-]+", "-", equipo.name).strip("-").lower() or "equipo"
    return Response(
        content=contenido,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="equipo-{nombre_archivo}.pdf"'},
    )


@router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
def borrar(team_id: int, usuario: CurrentUser, session: SessionDep):
    equipo = _equipo_propio(session, team_id, usuario)
    session.delete(equipo)
    session.commit()
