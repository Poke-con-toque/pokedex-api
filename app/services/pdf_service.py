"""Funciones PDF reutilizables para fichas y exportaciones."""

import logging
from io import BytesIO

import httpx
from fpdf import FPDF

logger = logging.getLogger("pokedex_api.pdf")


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


def crear_ficha_pokemon(pokemon: dict, descripcion: str | None = None) -> bytes:
    """Genera una ficha PDF; si el sprite falla, conserva el resto del documento."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 12, f"#{pokemon['id']} {pokemon['name'].title()}", new_x="LMARGIN", new_y="NEXT")

    sprite = _descargar_sprite(pokemon.get("sprite"))
    if sprite is not None:
        try:
            pdf.image(sprite, x=150, y=25, w=40, h=40)
        except Exception:
            logger.warning("El sprite de %s no tiene un formato compatible", pokemon["name"])

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 9, "Tipos", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=11)
    pdf.multi_cell(0, 7, ", ".join(pokemon.get("types", [])) or "Sin datos")

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 9, "Estadísticas", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=11)
    for etiqueta, clave in (("HP", "hp"), ("Attack", "attack"), ("Defense", "defense"), ("Speed", "speed")):
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

    return bytes(pdf.output())
