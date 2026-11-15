"""Servicio PDF: texto no Latin-1 y descarga de sprites."""

import httpx
import pytest
import respx

from app.services.pdf_service import (
    _texto,
    crear_ficha_pokemon,
    crear_pdf_equipo,
    descargar_sprite,
    descargar_sprites,
)
from tests.pokeapi_mocks import PNG_1X1

PIKACHU = {
    "id": 25,
    "name": "pikachu",
    "sprite": None,
    "types": ["electric"],
    "stats": {"hp": 35, "attack": 55, "defense": 40, "speed": 90},
    "abilities": ["static"],
}


def test_texto_traduce_caracteres_que_helvetica_no_admite():
    assert _texto("“Hola” — ‘adiós’…") == "\"Hola\" - 'adiós'..."
    assert _texto("Nidoran♀") == "Nidoran (hembra)"
    assert _texto("ñandú áéíóú ¡¿") == "ñandú áéíóú ¡¿"  # Latin-1 se conserva
    assert _texto("rayo ⚡ 雷") == "rayo ? ?"  # lo demás no rompe el PDF


@pytest.mark.parametrize(
    "descripcion",
    ["Normal", "Con “comillas”", "Con puntos…", "Con guion — largo", "Con emoji ⚡"],
)
def test_ficha_no_falla_con_textos_raros(descripcion):
    assert crear_ficha_pokemon(PIKACHU, descripcion).startswith(b"%PDF")


def test_ficha_no_falla_si_falta_una_estadistica():
    sin_hp = {**PIKACHU, "stats": {"hp": None, "attack": 1, "defense": 1, "speed": 1}}
    assert crear_ficha_pokemon(sin_hp).startswith(b"%PDF")


def test_ficha_con_sprite_valido_y_con_sprite_corrupto():
    con_imagen = crear_ficha_pokemon(PIKACHU, sprite=PNG_1X1)
    sin_imagen = crear_ficha_pokemon(PIKACHU)
    assert len(con_imagen) > len(sin_imagen)
    assert crear_ficha_pokemon(PIKACHU, sprite=b"no es una imagen").startswith(b"%PDF")


def test_pdf_equipo_con_nombre_raro():
    contenido = crear_pdf_equipo("Equipo “Élite” — 2026", "Los mejores…", [PIKACHU], [PNG_1X1])
    assert contenido.startswith(b"%PDF")


@pytest.mark.asyncio
@respx.mock
async def test_descargar_sprite():
    respx.get("https://sprites.test/25.png").respond(content=PNG_1X1)
    respx.get("https://sprites.test/404.png").respond(404)
    respx.get("https://sprites.test/lento.png").mock(side_effect=httpx.ReadTimeout("lento"))
    assert await descargar_sprite("https://sprites.test/25.png") == PNG_1X1
    assert await descargar_sprite("https://sprites.test/404.png") is None
    assert await descargar_sprite("https://sprites.test/lento.png") is None
    assert await descargar_sprite(None) is None


@pytest.mark.asyncio
@respx.mock
async def test_descargar_sprites_en_paralelo():
    respx.get("https://sprites.test/1.png").respond(content=PNG_1X1)
    resultado = await descargar_sprites(["https://sprites.test/1.png", None])
    assert resultado == [PNG_1X1, None]
