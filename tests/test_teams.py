"""Pruebas de propiedad, validación y orden de los equipos."""

from app.models import Team


def anadir_pokemon(client, headers, pokemon_id):
    respuesta = client.post(
        "/api/v1/pokedex",
        json={"pokemon_id": pokemon_id},
        headers=headers,
    )
    assert respuesta.status_code == 201


def test_crear_equipo_con_orden(client, auth_headers, pokeapi):
    anadir_pokemon(client, auth_headers, 25)
    anadir_pokemon(client, auth_headers, 4)

    respuesta = client.post(
        "/api/v1/teams",
        json={"name": "Equipo Kanto", "description": "Mi equipo", "pokemon_ids": [25, 4]},
        headers=auth_headers,
    )

    assert respuesta.status_code == 201
    equipo = respuesta.json()
    assert equipo["name"] == "Equipo Kanto"
    assert [(m["pokemon_id"], m["position"]) for m in equipo["members"]] == [(25, 1), (4, 2)]


def test_equipo_rechaza_mas_de_seis_pokemon(client, auth_headers):
    respuesta = client.post(
        "/api/v1/teams",
        json={"name": "Demasiados", "pokemon_ids": [1, 2, 3, 4, 5, 6, 7]},
        headers=auth_headers,
    )
    assert respuesta.status_code == 422


def test_equipo_rechaza_pokemon_que_no_estan_en_pokedex(client, auth_headers):
    respuesta = client.post(
        "/api/v1/teams",
        json={"name": "Fuera", "pokemon_ids": [25]},
        headers=auth_headers,
    )
    assert respuesta.status_code == 422


def test_listar_y_detalle_muestran_solo_equipos_propios(client, auth_headers, pokeapi):
    anadir_pokemon(client, auth_headers, 25)
    creado = client.post(
        "/api/v1/teams",
        json={"name": "Uno", "pokemon_ids": [25]},
        headers=auth_headers,
    ).json()

    lista = client.get("/api/v1/teams", headers=auth_headers)
    detalle = client.get(f"/api/v1/teams/{creado['id']}", headers=auth_headers)
    assert [e["id"] for e in lista.json()] == [creado["id"]]
    assert detalle.status_code == 200


def test_actualizar_equipo_reemplaza_miembros(client, auth_headers, pokeapi):
    anadir_pokemon(client, auth_headers, 25)
    anadir_pokemon(client, auth_headers, 4)
    creado = client.post(
        "/api/v1/teams",
        json={"name": "Inicial", "pokemon_ids": [25]},
        headers=auth_headers,
    ).json()

    actualizado = client.put(
        f"/api/v1/teams/{creado['id']}",
        json={"name": "Nuevo", "description": "Actualizado", "pokemon_ids": [4]},
        headers=auth_headers,
    )
    assert actualizado.status_code == 200
    assert actualizado.json()["name"] == "Nuevo"
    assert [(m["pokemon_id"], m["position"]) for m in actualizado.json()["members"]] == [(4, 1)]


def test_no_se_puede_ver_modificar_ni_borrar_equipo_ajeno(
    client, session, auth_headers, other_user
):
    equipo = Team(trainer_id=other_user.id, name="Ajeno")
    session.add(equipo)
    session.commit()
    ruta = f"/api/v1/teams/{equipo.id}"

    assert client.get(ruta, headers=auth_headers).status_code == 404
    assert client.put(ruta, json={"name": "Cambio", "pokemon_ids": []}, headers=auth_headers).status_code == 404
    assert client.delete(ruta, headers=auth_headers).status_code == 404
