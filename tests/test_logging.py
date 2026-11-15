"""Registro de peticiones y errores de entrada."""

import logging


def test_peticion_registra_metodo_ruta_y_estado(client, caplog):
    caplog.set_level(logging.INFO, logger="pokedex_api")
    respuesta = client.get("/health")

    assert respuesta.status_code == 200
    assert any(
        "GET /health → 200" in registro.getMessage()
        for registro in caplog.records
        if registro.name == "pokedex_api"
    )


def test_error_de_validacion_queda_registrado(client, auth_headers, caplog):
    caplog.set_level(logging.WARNING, logger="pokedex_api")
    respuesta = client.get(
        "/api/v1/pokemon/search?limit=0",
        headers=auth_headers,
    )

    assert respuesta.status_code == 422
    assert any(
        "Error de validación" in registro.getMessage()
        for registro in caplog.records
    )
