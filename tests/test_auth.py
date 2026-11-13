"""Registro, login y protección de endpoints con JWT."""

from datetime import UTC, datetime, timedelta

from jose import jwt

from app.auth import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.config import settings
from tests.conftest import PASSWORD

REGISTRO = "/api/v1/auth/register"
LOGIN = "/api/v1/auth/login"
ME = "/api/v1/auth/me"


def nuevo(username="misty", email="misty@ufv.es", password="Psyduck2026"):
    return {"username": username, "email": email, "password": password}


def test_hash_password_is_not_plain_text():
    hashed = hash_password("Pikachu2026")
    assert hashed != "Pikachu2026"
    assert hashed.startswith("$2b$")
    assert verify_password("Pikachu2026", hashed)
    assert not verify_password("Otra2026", hashed)


def test_register_user_success(client):
    respuesta = client.post(REGISTRO, json=nuevo())
    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["username"] == "misty"
    assert "hashed_password" not in cuerpo
    assert "password" not in cuerpo


def test_register_duplicate_username(client, test_user):
    respuesta = client.post(REGISTRO, json=nuevo(username="ash"))
    assert respuesta.status_code == 409


def test_register_duplicate_email(client, test_user):
    respuesta = client.post(REGISTRO, json=nuevo(email="ash@ufv.es"))
    assert respuesta.status_code == 409


def test_register_weak_password(client):
    for mala in ("corta1A", "sinmayuscula1", "SinNumeros"):
        respuesta = client.post(REGISTRO, json=nuevo(password=mala))
        assert respuesta.status_code == 422


def test_register_invalid_email(client):
    respuesta = client.post(REGISTRO, json=nuevo(email="no-es-un-email"))
    assert respuesta.status_code == 422


def test_login_success(client, test_user):
    respuesta = client.post(LOGIN, data={"username": "ash", "password": PASSWORD})
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["token_type"] == "bearer"
    claims = jwt.decode(
        cuerpo["access_token"], settings.secret_key, algorithms=[settings.algorithm]
    )
    assert claims["sub"] == "ash"
    assert claims["user_id"] == test_user.id
    assert claims["exp"] - claims["iat"] == 24 * 60 * 60


def test_login_invalid_credentials(client, test_user):
    mala = client.post(LOGIN, data={"username": "ash", "password": "Mala2026"})
    no_existe = client.post(LOGIN, data={"username": "nadie", "password": PASSWORD})
    assert mala.status_code == 401
    assert no_existe.status_code == 401
    # Mismo mensaje en los dos casos: no revelamos qué usuarios existen.
    assert mala.json() == no_existe.json()


def test_access_protected_endpoint_without_token(client):
    respuesta = client.get(ME)
    assert respuesta.status_code == 401


def test_access_protected_endpoint_with_token(client, auth_headers):
    respuesta = client.get(ME, headers=auth_headers)
    assert respuesta.status_code == 200
    assert respuesta.json()["username"] == "ash"


def test_invalid_token_rejected(client):
    respuesta = client.get(ME, headers={"Authorization": "Bearer inventado"})
    assert respuesta.status_code == 401


def test_expired_token_rejected(client, test_user):
    pasado = datetime.now(UTC) - timedelta(days=2)
    token = jwt.encode(
        {"sub": "ash", "user_id": test_user.id, "iat": pasado, "exp": pasado},
        settings.secret_key,
        algorithm=settings.algorithm,
    )
    respuesta = client.get(ME, headers={"Authorization": f"Bearer {token}"})
    assert respuesta.status_code == 401


def test_token_of_deleted_user_rejected(client, session, test_user):
    token = create_access_token("ash", test_user.id)
    session.delete(test_user)
    session.commit()
    respuesta = client.get(ME, headers={"Authorization": f"Bearer {token}"})
    assert respuesta.status_code == 401


def test_decode_invalid_token_returns_none():
    assert decode_access_token("no.es.un.jwt") is None
