"""Fixtures compartidas: base de datos en memoria y cliente de pruebas."""

import os

# Antes de importar la app: config.py exige SECRET_KEY y no queremos tocar pokedex.db.
os.environ.setdefault("SECRET_KEY", "clave-solo-para-tests")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.database import get_session
from app.main import app


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
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
