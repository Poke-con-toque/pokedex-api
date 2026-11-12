# Pokédex API

API REST con FastAPI para gestionar una Pokédex personal: busca Pokémon en [PokeAPI](https://pokeapi.co/), guárdalos en tu colección, marca los capturados y crea equipos de batalla.

> Práctica 1 · Módulo 2: APIs REST y Fundamentos de Integración · Sistemas de Información (UFV)

## Equipo

| Miembro | Usuario Git | Partes desarrolladas |
|---|---|---|
| Mario Linares | @mariolinaresmerino-commits | Estructura base, autenticación JWT, refresh token, rate limiting y CORS, CRUD de Pokédex, estadísticas, exportación de Pokédex, SECURITY.md |
| Adrián | @adriandczv | CI, cliente de PokeAPI, logging, búsqueda de Pokémon, ficha `/card`, equipos, exportación de equipos, API v2, despliegue |

## Instalación

Se necesita [uv](https://docs.astral.sh/uv/) (descarga Python 3.12 por sí solo).

```bash
git clone https://github.com/Poke-con-toque/pokedex-api.git
cd pokedex-api
uv sync                          # instala las versiones exactas de uv.lock
cp .env.example .env             # en Windows: copy .env.example .env
uv run python -c "import secrets; print(secrets.token_urlsafe(32))"   # pega el resultado en SECRET_KEY
```

Sin uv también funciona con pip: `pip install -r requirements.txt`.

> `requirements.txt` se genera desde `uv.lock`. Si añades una dependencia con `uv add`, regenéralo con
> `uv export --format requirements-txt --no-hashes --no-emit-project -o requirements.txt`.

## Ejecución

```bash
uv run uvicorn app.main:app --reload
```

- Comprobación: http://localhost:8000/health
- Documentación interactiva (Swagger): http://localhost:8000/docs

## Testing

```bash
uv run pytest --cov=app --cov-report=term-missing
```

## Flujo de trabajo

- `main`: versión estable y entregable.
- `develop`: integración de funcionalidades.
- `features/<nombre>`: una rama por funcionalidad; entra en `develop` por pull request revisado.
- `fix/<nombre>`: corrección de errores ya integrados.

*(Pendiente: Configuración, Endpoints, Decisiones de Diseño, Decisiones de Seguridad, Mejoras Futuras.)*
