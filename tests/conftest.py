"""Fixtures compartidas: base de datos en memoria y cliente de pruebas."""

import os

# Antes de importar la app: config.py exige SECRET_KEY y no queremos tocar pokedex.db.
os.environ.setdefault("SECRET_KEY", "clave-solo-para-tests")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

import bcrypt
import httpx
import pytest
import respx
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.auth import hash_password
from app.database import get_session
from app.limits import limiter
from app.main import app
from app.models import User
from app.services.pokeapi_service import limpiar_cache
from tests.pokeapi_mocks import (
    BASE,
    DATOS,
    PNG_1X1,
    SPRITES,
    lista_bruta,
    pokemon_bruto,
)

PASSWORD = "Pikachu2026"


_gensalt = bcrypt.gensalt


@pytest.fixture(autouse=True)
def bcrypt_rapido(monkeypatch):
    # En producción bcrypt usa 12 rondas (lento a propósito). En los tests bastan 4.
    monkeypatch.setattr(bcrypt, "gensalt", lambda: _gensalt(rounds=4))


@pytest.fixture(autouse=True)
def cache_vacia():
    # La caché de la PokeAPI es global: se vacía para que cada test parta de cero.
    limpiar_cache()
    yield
    limpiar_cache()


@pytest.fixture
def session():
    # Una base de datos nueva en memoria para cada test: nada se arrastra de uno a otro.
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture
def client(session):
    # El contador del limitador vive en memoria: sin esto, unos tests agotarían el cupo de otros.
    limiter.reset()
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def crear_usuario(session, username: str) -> User:
    usuario = User(
        username=username,
        email=f"{username}@ufv.es",
        hashed_password=hash_password(PASSWORD),
    )
    session.add(usuario)
    session.commit()
    session.refresh(usuario)
    return usuario


def cabeceras(client, username: str) -> dict:
    respuesta = client.post(
        "/api/v1/auth/login", data={"username": username, "password": PASSWORD}
    )
    return {"Authorization": f"Bearer {respuesta.json()['access_token']}"}


@pytest.fixture
def test_user(session) -> User:
    return crear_usuario(session, "ash")


@pytest.fixture
def auth_headers(client, test_user) -> dict:
    return cabeceras(client, test_user.username)


@pytest.fixture
def other_user(session) -> User:
    return crear_usuario(session, "gary")


@pytest.fixture
def other_headers(client, other_user) -> dict:
    return cabeceras(client, other_user.username)


@pytest.fixture
def pokeapi():
    """PokeAPI simulada: conoce los Pokémon de pokeapi_mocks.DATOS y da 404 al resto."""
    with respx.mock(assert_all_called=False) as simulada:
        for pid, (nombre, *_resto) in DATOS.items():
            for clave in (pid, nombre):
                simulada.get(f"{BASE}/pokemon/{clave}").respond(json=pokemon_bruto(pid))
        simulada.get(url__regex=rf"^{BASE}/pokemon\?limit=\d+&offset=\d+$").mock(
            side_effect=lambda peticion: httpx.Response(
                200,
                json=lista_bruta(
                    int(peticion.url.params["limit"]), int(peticion.url.params["offset"])
                ),
            )
        )
        simulada.get(url__startswith=f"{BASE}/pokemon/").respond(404)
        # Los sprites también se simulan: los PDF los descargan y los tests no salen a Internet.
        simulada.get(url__startswith=SPRITES).respond(content=PNG_1X1)
        yield simulada
