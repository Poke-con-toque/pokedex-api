"""Funciones PDF reutilizables para fichas de Pokémon y equipos."""

import asyncio
import logging
from io import BytesIO

import httpx
from fpdf import FPDF
from fpdf.errors import FPDFException

logger = logging.getLogger("pokedex_api.pdf")
ESTADISTICAS = (("HP", "hp"), ("Attack", "attack"), ("Defense", "defense"), ("Speed", "speed"))

# Las fuentes estándar del PDF (Helvetica) sólo admiten Latin-1: las tildes y la ñ sí,
# pero no comillas tipográficas, guiones largos o puntos suspensivos, que sí aparecen
# en las descripciones de la PokeAPI o en el nombre que el usuario da a un equipo.
# Sin esta traducción, fpdf2 lanza una excepción y el endpoint responde 500.
EQUIVALENCIAS = str.maketrans(
    {
        "‘": "'", "’": "'", "‚": "'", "“": '"', "”": '"', "„": '"',
        "–": "-", "—": "-", "―": "-", "−": "-",
        "…": "...", "•": "·", " ": " ", " ": " ", " ": " ",
        "♀": " (hembra)", "♂": " (macho)",
    }
)


def _texto(valor: object) -> str:
    """Convierte cualquier texto a algo que Helvetica pueda escribir."""
    texto = str(valor).translate(EQUIVALENCIAS)
    # Lo que aún no sea Latin-1 (emojis, otros alfabetos…) se sustituye por «?».
    return texto.encode("latin-1", errors="replace").decode("latin-1")


async def descargar_sprite(url: str | None) -> bytes | None:
    """Descarga un sprite sin bloquear la API; si falla, la ficha se genera sin imagen."""
    if not url:
        return None
    try:
        async with httpx.AsyncClient(timeout=3.0) as cliente:
            respuesta = await cliente.get(url)
        respuesta.raise_for_status()
        return respuesta.content
    except httpx.HTTPError as error:
        logger.warning("No se pudo descargar el sprite %s: %s", url, error)
        return None


async def descargar_sprites(urls: list[str | None]) -> list[bytes | None]:
    """Descarga varios sprites a la vez, no uno detrás de otro."""
    return list(await asyncio.gather(*(descargar_sprite(url) for url in urls)))


def _titulo(pdf: FPDF, texto: str, tamano: int = 12) -> None:
    pdf.set_font("Helvetica", "B", tamano)
    pdf.cell(0, 9 if tamano <= 12 else 12, _texto(texto), new_x="LMARGIN", new_y="NEXT")


def _parrafo(pdf: FPDF, texto: str) -> None:
    pdf.set_font("Helvetica", size=11)
    pdf.multi_cell(0, 7, _texto(texto), new_x="LMARGIN", new_y="NEXT")


def agregar_ficha_pokemon(
    pdf: FPDF,
    pokemon: dict,
    descripcion: str | None = None,
    sprite: bytes | None = None,
) -> None:
    """Añade a la página activa una ficha de Pokémon."""
    _titulo(pdf, f"#{pokemon['id']} {pokemon['name'].title()}", tamano=20)

    if sprite is not None:
        try:
            pdf.image(BytesIO(sprite), x=150, y=25, w=40, h=40)
        except (FPDFException, OSError, TypeError, ValueError):
            logger.warning("El sprite de %s no tiene un formato compatible", pokemon["name"])

    _titulo(pdf, "Tipos")
    _parrafo(pdf, ", ".join(pokemon.get("types", [])) or "Sin datos")

    _titulo(pdf, "Estadísticas")
    pdf.set_font("Helvetica", size=11)
    for etiqueta, clave in ESTADISTICAS:
        valor = (pokemon.get("stats") or {}).get(clave)
        linea = f"{etiqueta}: {valor if valor is not None else '-'}"
        pdf.cell(0, 7, _texto(linea), new_x="LMARGIN", new_y="NEXT")

    _titulo(pdf, "Habilidades")
    _parrafo(pdf, ", ".join(pokemon.get("abilities", [])) or "Sin datos")

    if descripcion:
        _titulo(pdf, "Descripción")
        _parrafo(pdf, descripcion)


def crear_ficha_pokemon(
    pokemon: dict, descripcion: str | None = None, sprite: bytes | None = None
) -> bytes:
    """Genera una ficha PDF; si no hay sprite, conserva el resto del documento."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    agregar_ficha_pokemon(pdf, pokemon, descripcion, sprite)
    return bytes(pdf.output())


def calcular_estadisticas_equipo(pokemon: list[dict]) -> dict:
    """Calcula sumas, medias y tipos cubiertos por el equipo."""
    n = len(pokemon)
    sumas = {
        clave: sum((p.get("stats") or {}).get(clave) or 0 for p in pokemon)
        for _etiqueta, clave in ESTADISTICAS
    }
    medias = {clave: round(valor / n, 1) if n else 0.0 for clave, valor in sumas.items()}
    tipos = sorted({tipo for p in pokemon for tipo in p.get("types", [])})
    return {"sum": sumas, "average": medias, "types": tipos}


def crear_pdf_equipo(
    nombre: str,
    descripcion: str | None,
    pokemon: list[dict],
    sprites: list[bytes | None] | None = None,
) -> bytes:
    """Genera un PDF del equipo con una ficha por Pokémon y estadísticas combinadas."""
    sprites = sprites or [None] * len(pokemon)
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    _titulo(pdf, f"Equipo: {nombre}", tamano=20)
    if descripcion:
        _parrafo(pdf, descripcion)

    for ficha, sprite in zip(pokemon, sprites, strict=True):
        pdf.add_page()
        agregar_ficha_pokemon(pdf, ficha, sprite=sprite)

    calculadas = calcular_estadisticas_equipo(pokemon)
    pdf.add_page()
    _titulo(pdf, "Estadísticas combinadas", tamano=18)
    pdf.set_font("Helvetica", size=11)
    for etiqueta, clave in ESTADISTICAS:
        linea = (
            f"{etiqueta}: suma {calculadas['sum'][clave]} · "
            f"media {calculadas['average'][clave]}"
        )
        pdf.cell(0, 8, _texto(linea), new_x="LMARGIN", new_y="NEXT")
    tipos = ", ".join(calculadas["types"]) or "Sin datos"
    pdf.cell(0, 8, _texto(f"Tipos cubiertos: {tipos}"))
    return bytes(pdf.output())
