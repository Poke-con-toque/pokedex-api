"""Estadísticas de la Pokédex (Grupo 3 del enunciado)."""

from datetime import date, datetime, timedelta

from app.models import PokedexEntry, ahora
from app.routers.pokedex import racha_de_capturas, tipo_mas_comun

STATS = "/api/v1/pokedex/stats"


def entrada(session, usuario, pokemon_id, tipos, capturado=False, fecha=None, favorito=False):
    session.add(
        PokedexEntry(
            owner_id=usuario.id,
            pokemon_id=pokemon_id,
            pokemon_name=f"pokemon-{pokemon_id}",
            pokemon_types=tipos,
            is_captured=capturado,
            capture_date=fecha,
            favorite=favorito,
        )
    )
    session.commit()


def test_stats_empty_pokedex(client, auth_headers):
    respuesta = client.get(STATS, headers=auth_headers)
    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "total_pokemon": 0,
        "captured": 0,
        "favorites": 0,
        "completion_percentage": 0.0,
        "most_common_type": None,
        "capture_streak_days": 0,
    }


def test_stats_counts_and_percentage(client, session, auth_headers, test_user, monkeypatch):
    from app.config import settings

    hoy = ahora()
    entrada(session, test_user, 25, "electric", capturado=True, fecha=hoy)
    entrada(session, test_user, 1, "grass,poison", favorito=True)
    entrada(session, test_user, 4, "fire")
    stats = client.get(STATS, headers=auth_headers).json()
    assert stats["total_pokemon"] == 3
    assert stats["captured"] == 1
    assert stats["favorites"] == 1
    assert stats["completion_percentage"] == 0.1  # 1 / 1025 * 100, redondeado

    monkeypatch.setattr(settings, "total_pokemon", 4)
    stats_configurada = client.get(STATS, headers=auth_headers).json()
    assert stats_configurada["completion_percentage"] == 25.0


def test_stats_most_common_type(client, session, auth_headers, test_user):
    entrada(session, test_user, 7, "water")
    entrada(session, test_user, 8, "water")
    entrada(session, test_user, 1, "grass,poison")
    entrada(session, test_user, 43, "grass,poison")
    entrada(session, test_user, 54, "water")
    assert client.get(STATS, headers=auth_headers).json()["most_common_type"] == "water"


def test_stats_capture_streak(client, session, auth_headers, test_user):
    hoy = ahora()
    for dias_atras, pid in ((0, 1), (1, 4), (2, 7), (4, 25)):  # hueco hace 3 días
        entrada(session, test_user, pid, "normal", capturado=True, fecha=hoy - timedelta(days=dias_atras))
    assert client.get(STATS, headers=auth_headers).json()["capture_streak_days"] == 3


def test_stats_only_count_own_entries(client, session, auth_headers, other_user):
    entrada(session, other_user, 25, "electric", capturado=True, fecha=ahora())
    stats = client.get(STATS, headers=auth_headers).json()
    assert stats["total_pokemon"] == 0
    assert stats["capture_streak_days"] == 0


def test_stats_requires_token(client):
    assert client.get(STATS).status_code == 401


# ─────────────────────────── Funciones de cálculo ───────────────────────────


def test_tipo_mas_comun():
    assert tipo_mas_comun([]) is None
    assert tipo_mas_comun([None, ""]) is None
    assert tipo_mas_comun(["fire", "grass,poison", "poison"]) == "poison"
    assert tipo_mas_comun(["water", "fire"]) == "fire"  # empate → orden alfabético


def test_racha_de_capturas():
    hoy = date(2026, 11, 15)
    a = lambda d: datetime(2026, 11, d, 12, 0)
    assert racha_de_capturas([], hoy) == 0
    assert racha_de_capturas([a(15), a(14), a(13)], hoy) == 3
    assert racha_de_capturas([a(15), a(15), a(14)], hoy) == 2  # varias el mismo día cuentan una
    assert racha_de_capturas([a(14), a(13)], hoy) == 2  # hoy aún no, la racha sigue viva
    assert racha_de_capturas([a(13), a(12)], hoy) == 0  # ayer no hubo: racha rota
    assert racha_de_capturas([a(15), a(13)], hoy) == 1
