"""CRUD de la Pokédex personal: cada usuario sólo ve y toca lo suyo."""

import csv
import io
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import func, select

from app.config import settings
from app.dependencies import CurrentUser, ServicioPokeAPI, SessionDep
from app.limits import LIMITE_GENERAL, LIMITE_POKEAPI, limiter
from app.models import (
    PokedexEntry,
    PokedexEntryCreate,
    PokedexEntryRead,
    PokedexEntryUpdate,
    PokedexStats,
    TeamMember,
    ahora,
)
from app.services.pdf_service import crear_pdf_pokedex

router = APIRouter(prefix="/pokedex", tags=["pokedex"])

# El texto que llega en ?sort= se traduce a columna aquí. Nunca se pega en el SQL.
ORDENABLE = {
    "pokemon_id": PokedexEntry.pokemon_id,
    "pokemon_name": PokedexEntry.pokemon_name,
    "capture_date": PokedexEntry.capture_date,
}


@dataclass
class FiltrosPokedex:
    """Filtros, orden y paginación del listado. Los comparten /api/v1 y /api/v2."""

    captured: bool | None = None
    favorite: bool | None = None
    sort: Literal["pokemon_id", "pokemon_name", "capture_date"] = "pokemon_id"
    order: Literal["asc", "desc"] = "asc"
    limit: int = Query(default=20, ge=1, le=100)
    offset: int = Query(default=0, ge=0)


Filtros = Annotated[FiltrosPokedex, Depends()]


def entradas_filtradas(session, usuario_id: int, filtros: FiltrosPokedex) -> list[PokedexEntry]:
    consulta = select(PokedexEntry).where(PokedexEntry.owner_id == usuario_id)
    if filtros.captured is not None:
        consulta = consulta.where(PokedexEntry.is_captured == filtros.captured)
    if filtros.favorite is not None:
        consulta = consulta.where(PokedexEntry.favorite == filtros.favorite)
    columna = ORDENABLE[filtros.sort]
    consulta = consulta.order_by(columna.desc() if filtros.order == "desc" else columna.asc())
    return session.exec(consulta.offset(filtros.offset).limit(filtros.limit)).all()


@router.post("", response_model=PokedexEntryRead, status_code=status.HTTP_201_CREATED)
@limiter.limit(LIMITE_POKEAPI)  # comprueba el Pokémon en la PokeAPI
async def anadir(
    request: Request,
    datos: PokedexEntryCreate,
    usuario: CurrentUser,
    session: SessionDep,
    poke: ServicioPokeAPI,
):
    ya_esta = session.exec(
        select(PokedexEntry).where(
            PokedexEntry.owner_id == usuario.id,
            PokedexEntry.pokemon_id == datos.pokemon_id,
        )
    ).first()
    if ya_esta:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya está en tu Pokédex")

    info = await poke.get_pokemon(datos.pokemon_id)
    entrada = PokedexEntry(
        **datos.model_dump(),
        owner_id=usuario.id,
        pokemon_name=info["name"],
        pokemon_sprite=info["sprite"],
        pokemon_types=",".join(info["types"]),
        capture_date=ahora() if datos.is_captured else None,
    )
    session.add(entrada)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya está en tu Pokédex")
    session.refresh(entrada)
    return entrada


@router.get("", response_model=list[PokedexEntryRead])
@limiter.limit(LIMITE_GENERAL)
def listar(request: Request, usuario: CurrentUser, session: SessionDep, filtros: Filtros):
    return entradas_filtradas(session, usuario.id, filtros)


def _contar(session, *condiciones) -> int:
    consulta = select(func.count()).select_from(PokedexEntry)
    for condicion in condiciones:
        consulta = consulta.where(condicion)
    return session.exec(consulta).one()


def tipo_mas_comun(tipos_por_entrada: list[str | None]) -> str | None:
    """Tipo que más se repite en la Pokédex; si empatan, el primero alfabéticamente."""
    contador = Counter(tipo for tipos in tipos_por_entrada if tipos for tipo in tipos.split(","))
    if not contador:
        return None
    return min(contador, key=lambda tipo: (-contador[tipo], tipo))


def racha_de_capturas(fechas: list[datetime], hoy: date) -> int:
    """Días seguidos con al menos una captura, contando hacia atrás desde hoy.

    Si hoy todavía no has capturado, la racha cuenta desde ayer: no se pierde
    hasta que termina el día sin capturar.
    """
    dias = {fecha.date() for fecha in fechas}
    dia = hoy if hoy in dias else hoy - timedelta(days=1)
    racha = 0
    while dia in dias:
        racha += 1
        dia -= timedelta(days=1)
    return racha


# /stats va ANTES que /{entry_id}: si no, FastAPI intentaría leer "stats" como un id.
@router.get("/stats", response_model=PokedexStats)
@limiter.limit(LIMITE_GENERAL)
def estadisticas(request: Request, usuario: CurrentUser, session: SessionDep):
    mias = PokedexEntry.owner_id == usuario.id
    total = _contar(session, mias)
    capturados = _contar(session, mias, PokedexEntry.is_captured)
    favoritos = _contar(session, mias, PokedexEntry.favorite)
    # El porcentaje se calcula respecto a todas las especies disponibles (1025 por defecto).
    porcentaje = round(100 * capturados / settings.total_pokemon, 1) if settings.total_pokemon else 0.0
    tipos = session.exec(select(PokedexEntry.pokemon_types).where(mias)).all()
    fechas = session.exec(
        select(PokedexEntry.capture_date).where(
            mias, PokedexEntry.is_captured, PokedexEntry.capture_date.is_not(None)
        )
    ).all()
    return {
        "total_pokemon": total,
        "captured": capturados,
        "favorites": favoritos,
        "completion_percentage": porcentaje,
        "most_common_type": tipo_mas_comun(tipos),
        "capture_streak_days": racha_de_capturas(fechas, ahora().date()),
    }


COLUMNAS_EXPORTACION = (
    "pokemon_id",
    "pokemon_name",
    "nickname",
    "types",
    "is_captured",
    "capture_date",
    "favorite",
    "notes",
)


def _fila(entrada: PokedexEntry) -> dict:
    return {
        "pokemon_id": entrada.pokemon_id,
        "pokemon_name": entrada.pokemon_name,
        "nickname": entrada.nickname,
        "types": entrada.pokemon_types or "",
        "is_captured": entrada.is_captured,
        "capture_date": entrada.capture_date.strftime("%Y-%m-%d %H:%M") if entrada.capture_date else "",
        "favorite": entrada.favorite,
        "notes": entrada.notes,
    }


def _celda_csv(valor) -> str:
    """Evita fórmulas en Excel incluso si comienzan tras espacios o controles."""
    texto = "" if valor is None else str(valor)
    potencial_formula = texto.lstrip(" \t\r\n")
    return f"'{texto}" if potencial_formula[:1] in ("=", "+", "-", "@") else texto

def _csv(filas: list[dict]) -> bytes:
    salida = io.StringIO()
    escritor = csv.writer(salida)
    escritor.writerow(COLUMNAS_EXPORTACION)
    for fila in filas:
        escritor.writerow(_celda_csv(fila[columna]) for columna in COLUMNAS_EXPORTACION)
    # BOM UTF-8: así Excel abre bien las tildes y la ñ.
    return ("\ufeff" + salida.getvalue()).encode("utf-8")


# /export va ANTES que /{entry_id}, por el mismo motivo que /stats.
@router.get(
    "/export",
    responses={
        200: {
            "content": {"text/csv": {}, "application/pdf": {}},
            "description": "Archivo descargable con la Pokédex",
        }
    },
)
@limiter.limit(LIMITE_GENERAL)
def exportar(
    request: Request,
    usuario: CurrentUser,
    session: SessionDep,
    format: Literal["csv", "pdf"] = "csv",
    captured: bool | None = None,
    favorite: bool | None = None,
):
    """Descarga la Pokédex completa en CSV o PDF, con filtros opcionales."""
    consulta = select(PokedexEntry).where(PokedexEntry.owner_id == usuario.id)
    if captured is not None:
        consulta = consulta.where(PokedexEntry.is_captured == captured)
    if favorite is not None:
        consulta = consulta.where(PokedexEntry.favorite == favorite)
    filas = [_fila(e) for e in session.exec(consulta.order_by(PokedexEntry.pokemon_id)).all()]

    if format == "pdf":
        descripcion = ", ".join(
            texto
            for activo, texto in (
                (captured is True, "solo capturados"),
                (captured is False, "solo sin capturar"),
                (favorite is True, "solo favoritos"),
                (favorite is False, "sin favoritos"),
            )
            if activo
        ) or "todos"
        contenido, tipo = crear_pdf_pokedex(usuario.username, filas, descripcion), "application/pdf"
    else:
        contenido, tipo = _csv(filas), "text/csv; charset=utf-8"

    return Response(
        content=contenido,
        media_type=tipo,
        headers={"Content-Disposition": f'attachment; filename="pokedex.{format}"'},
    )


def _entrada_propia(session, entry_id: int, usuario) -> PokedexEntry:
    entrada = session.get(PokedexEntry, entry_id)
    # 404 también si es de otro: no confirmamos que exista.
    if entrada is None or entrada.owner_id != usuario.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No está en tu Pokédex")
    return entrada


@router.get("/{entry_id}", response_model=PokedexEntryRead)
@limiter.limit(LIMITE_GENERAL)
def detalle(request: Request, entry_id: int, usuario: CurrentUser, session: SessionDep):
    return _entrada_propia(session, entry_id, usuario)


@router.patch("/{entry_id}", response_model=PokedexEntryRead)
@limiter.limit(LIMITE_GENERAL)
def actualizar(
    request: Request, entry_id: int, datos: PokedexEntryUpdate, usuario: CurrentUser, session: SessionDep
):
    entrada = _entrada_propia(session, entry_id, usuario)
    cambios = datos.model_dump(exclude_unset=True)
    # Regla de negocio: capturar pone fecha (si no la mandan); soltar la quita.
    if cambios.get("is_captured") is True and "capture_date" not in cambios:
        if entrada.capture_date is None:
            cambios["capture_date"] = ahora()
    elif cambios.get("is_captured") is False:
        cambios["capture_date"] = None
    entrada.sqlmodel_update(cambios)
    session.add(entrada)
    session.commit()
    session.refresh(entrada)
    return entrada


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(LIMITE_GENERAL)
def borrar(request: Request, entry_id: int, usuario: CurrentUser, session: SessionDep):
    entrada = _entrada_propia(session, entry_id, usuario)
    # Si estaba en algún equipo, sale también de él: no dejamos miembros huérfanos.
    for miembro in session.exec(
        select(TeamMember).where(TeamMember.pokedex_entry_id == entrada.id)
    ):
        session.delete(miembro)
    session.delete(entrada)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
