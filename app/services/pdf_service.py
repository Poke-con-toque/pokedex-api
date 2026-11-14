"""Funciones PDF reutilizables para fichas de Pokémon y equipos."""

import logging
from io import BytesIO

import httpx
from fpdf import FPDF
from fpdf.errors import FPDFException

logger = logging.getLogger("pokedex_api.pdf")
ESTADISTICAS = (("HP", "hp"), ("Attack", "attack"), ("Defense", "defense"), ("Speed", "speed"))


def _descargar_sprite(url: str | None) -> BytesIO | None:
    if not url:
        return None
    try:
        respuesta = httpx.get(url, timeout=3.0)
        respuesta.raise_for_status()
        return BytesIO(respuesta.content)
    except (httpx.HTTPError, OSError) as error:
        logger.warning("No se pudo descargar el sprite %s: %s", url, error)
        return None


def agregar_ficha_pokemon(pdf: FPDF, pokemon: dict, descripcion: str | None = None) -> None:
    """Añade a la página activa una ficha de Pokémon."""
    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 12, f"#{pokemon['id']} {pokemon['name'].title()}", new_x="LMARGIN", new_y="NEXT")

    sprite = _descargar_sprite(pokemon.get("sprite"))
    if sprite is not None:
        try:
            pdf.image(sprite, x=150, y=25, w=40, h=40)
        except (FPDFException, OSError, TypeError, ValueError):
            logger.warning("El sprite de %s no tiene un formato compatible", pokemon["name"])

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 9, "Tipos", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=11)
    pdf.multi_cell(0, 7, ", ".join(pokemon.get("types", [])) or "Sin datos")

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 9, "Estadísticas", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=11)
    for etiqueta, clave in ESTADISTICAS:
        valor = (pokemon.get("stats") or {}).get(clave)
        pdf.cell(0, 7, f"{etiqueta}: {valor if valor is not None else '—'}", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 9, "Habilidades", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=11)
    pdf.multi_cell(0, 7, ", ".join(pokemon.get("abilities", [])) or "Sin datos")

    if descripcion:
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 9, "Descripción", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", size=11)
        pdf.multi_cell(0, 7, descripcion)


def crear_ficha_pokemon(pokemon: dict, descripcion: str | None = None) -> bytes:
    """Genera una ficha PDF; si el sprite falla, conserva el resto del documento."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    agregar_ficha_pokemon(pdf, pokemon, descripcion)
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


def crear_pdf_equipo(nombre: str, descripcion: str | None, pokemon: list[dict]) -> bytes:
    """Genera un PDF del equipo con una ficha por Pokémon y estadísticas combinadas."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 12, f"Equipo: {nombre}", new_x="LMARGIN", new_y="NEXT")
    if descripcion:
        pdf.set_font("Helvetica", size=11)
        pdf.multi_cell(0, 7, descripcion)

    for ficha in pokemon:
        pdf.add_page()
        agregar_ficha_pokemon(pdf, ficha)

    calculadas = calcular_estadisticas_equipo(pokemon)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 12, "Estadísticas combinadas", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=11)
    for etiqueta, clave in ESTADISTICAS:
        pdf.cell(
            0,
            8,
            f"{etiqueta}: suma {calculadas['sum'][clave]} · media {calculadas['average'][clave]}",
            new_x="LMARGIN",
            new_y="NEXT",
        )
    pdf.cell(0, 8, f"Tipos cubiertos: {', '.join(calculadas['types']) or 'Sin datos'}")
    return bytes(pdf.output())
