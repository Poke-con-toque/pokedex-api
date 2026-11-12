"""Arranque de la app, configuración y modelos."""

import pytest
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from app.config import Settings
from app.database import get_session
from app.models import PokedexEntry, PokedexEntryCreate, User, UserCreate, UserRead


def test_health(client):
    respuesta = client.get("/health")
    assert respuesta.status_code == 200
    assert respuesta.json() == {"status": "ok"}


def test_docs_title(client):
    assert client.get("/openapi.json").json()["info"]["title"] == "Pokédex API"


def test_settings_require_secret_key(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_get_session_yields_session():
    generador = get_session()
    sesion = next(generador)
    assert sesion is not None
    generador.close()


def test_user_create_password_rules():
    UserCreate(username="ash", email="ash@ufv.es", password="Pikachu25")
    for mala in ("corta1A", "sinmayuscula1", "SinNumeros"):
        with pytest.raises(ValidationError):
            UserCreate(username="ash", email="ash@ufv.es", password=mala)


def test_user_create_invalid_email():
    with pytest.raises(ValidationError):
        UserCreate(username="ash", email="no-es-un-email", password="Pikachu25")


def test_user_read_hides_password():
    assert "hashed_password" not in UserRead.model_fields
    assert "password" not in UserRead.model_fields


def test_pokemon_id_range():
    PokedexEntryCreate(pokemon_id=25)
    for malo in (0, 1026):
        with pytest.raises(ValidationError):
            PokedexEntryCreate(pokemon_id=malo)


def test_pokedex_unique_owner_pokemon(session):
    usuario = User(username="ash", email="ash@ufv.es", hashed_password="x")
    session.add(usuario)
    session.commit()
    for _ in range(2):
        session.add(
            PokedexEntry(owner_id=usuario.id, pokemon_id=25, pokemon_name="pikachu")
        )
    with pytest.raises(IntegrityError):
        session.commit()
