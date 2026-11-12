# Pokédex API

API REST con FastAPI para gestionar una Pokédex personal: busca Pokémon en [PokeAPI](https://pokeapi.co/), guárdalos en tu colección, marca los capturados y crea equipos de batalla.

> Práctica 1 · Módulo 2: APIs REST y Fundamentos de Integración · Sistemas de Información (UFV)

## Equipo

| Miembro | Usuario Git | Partes desarrolladas |
|---|---|---|
| Miembro A | @usuario-a | Estructura base, autenticación JWT, refresh token, rate limiting y CORS, CRUD de Pokédex, estadísticas, exportación de Pokédex, SECURITY.md |
| Miembro B | @usuario-b | CI, cliente de PokeAPI, logging, búsqueda de Pokémon, ficha `/card`, equipos, exportación de equipos, API v2, despliegue |

## Instalación

```bash
git clone https://github.com/Poke-con-toque/pokedex-api.git
cd pokedex-api
python -m venv .venv
source .venv/bin/activate        # En Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # y rellena los valores
```

## Ejecución

```bash
uvicorn app.main:app --reload
```

Documentación interactiva (Swagger): http://localhost:8000/docs

## Testing

```bash
pytest --cov=app --cov-report=term-missing
```

## Flujo de trabajo

- `main`: versión estable y entregable.
- `develop`: integración de funcionalidades.
- `features/<nombre>`: una rama por funcionalidad; entra en `develop` por pull request revisado.
- `fix/<nombre>`: corrección de errores ya integrados.

*(Pendiente: Configuración, Endpoints, Decisiones de Diseño, Decisiones de Seguridad, Mejoras Futuras.)*
