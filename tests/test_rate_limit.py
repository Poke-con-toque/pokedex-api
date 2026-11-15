"""Rate limiting diferenciado por tipo de endpoint y configuración CORS."""

import logging

LOGIN = "/api/v1/auth/login"
REGISTRO = "/api/v1/auth/register"


def test_rate_limit_exceeded(client):
    """Login: 10 intentos por minuto; el 11.º devuelve 429 Too Many Requests."""
    datos = {"username": "nadie", "password": "Mala2026"}
    for _ in range(10):
        assert client.post(LOGIN, data=datos).status_code == 401
    respuesta = client.post(LOGIN, data=datos)
    assert respuesta.status_code == 429
    # Mismo formato de error que el resto de la API.
    assert respuesta.json() == {"detail": "Demasiadas peticiones: límite de 10 per 1 minute"}


def test_register_limited_to_5_per_hour(client):
    for i in range(5):
        datos = {"username": f"ent{i}", "email": f"ent{i}@ufv.es", "password": "Pikachu2026"}
        assert client.post(REGISTRO, json=datos).status_code == 201
    extra = {"username": "ent5", "email": "ent5@ufv.es", "password": "Pikachu2026"}
    assert client.post(REGISTRO, json=extra).status_code == 429


def test_pokeapi_endpoints_limited_to_30_per_minute(client, auth_headers, pokeapi):
    for _ in range(30):
        assert client.get("/api/v1/pokemon/pikachu", headers=auth_headers).status_code == 200
    assert client.get("/api/v1/pokemon/pikachu", headers=auth_headers).status_code == 429


def test_authenticated_endpoints_limited_to_100_per_minute(client, auth_headers):
    for _ in range(100):
        assert client.get("/api/v1/pokedex", headers=auth_headers).status_code == 200
    assert client.get("/api/v1/pokedex", headers=auth_headers).status_code == 429


def test_limits_are_counted_per_endpoint(client, auth_headers, pokeapi):
    for _ in range(30):
        client.get("/api/v1/pokemon/search?limit=1", headers=auth_headers)
    assert client.get("/api/v1/pokemon/search?limit=1", headers=auth_headers).status_code == 429
    # Agotar la búsqueda no bloquea el resto de la API.
    assert client.get("/api/v1/pokedex", headers=auth_headers).status_code == 200


def test_health_is_not_limited(client):
    for _ in range(150):
        assert client.get("/health").status_code == 200


def test_rate_limit_is_logged(client, caplog):
    datos = {"username": "nadie", "password": "Mala2026"}
    with caplog.at_level(logging.WARNING, logger="pokedex_api"):
        for _ in range(11):
            client.post(LOGIN, data=datos)
    assert "Límite excedido: POST /api/v1/auth/login" in caplog.text


# ─────────────────────────── CORS ───────────────────────────


def preflight(client, origen, metodo="PUT"):
    return client.options(
        "/api/v1/teams/1",
        headers={
            "Origin": origen,
            "Access-Control-Request-Method": metodo,
            "Access-Control-Request-Headers": "Authorization, Content-Type",
        },
    )


def test_cors_allows_configured_origin(client):
    respuesta = preflight(client, "http://localhost:5173")
    assert respuesta.status_code == 200
    assert respuesta.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "PUT" in respuesta.headers["access-control-allow-methods"]
    assert respuesta.headers["access-control-max-age"] == "3600"


def test_cors_rejects_unknown_origin(client):
    respuesta = preflight(client, "https://web-maliciosa.example")
    assert respuesta.status_code == 400
    assert "access-control-allow-origin" not in respuesta.headers


def test_cors_rejects_unlisted_method(client):
    assert preflight(client, "http://localhost:5173", metodo="TRACE").status_code == 400


def test_cors_header_on_simple_request(client):
    respuesta = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert respuesta.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_every_api_endpoint_has_a_rate_limit():
    """Si alguien añade un endpoint y olvida @limiter.limit, este test falla."""
    from app.limits import limiter
    from app.routers import auth, pokedex, pokemon, teams, v2

    sin_limite = [
        f"{ruta.methods} {ruta.path}"
        for modulo in (auth, pokemon, pokedex, teams, v2)
        for ruta in modulo.router.routes
        if f"{ruta.endpoint.__module__}.{ruta.endpoint.__name__}" not in limiter._route_limits
    ]
    assert sin_limite == []
