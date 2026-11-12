"""Punto de entrada de la Pokédex API."""

from fastapi import FastAPI

app = FastAPI(
    title="Pokédex API",
    description="API REST para gestionar una Pokédex personal usando datos de PokeAPI.",
    version="0.1.0",
)


@app.get("/", tags=["health"])
async def root() -> dict:
    """Comprobación rápida de que la API está en marcha."""
    return {"status": "ok", "docs": "/docs"}
