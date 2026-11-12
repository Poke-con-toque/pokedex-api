"""Punto de entrada de la Pokédex API."""

from fastapi import FastAPI

app = FastAPI(
    title="Pokédex API",
    version="1.0.0",
    description="API REST del Pokédex personal · Práctica 1",
)


@app.get("/health", tags=["sistema"])
def health():
    return {"status": "ok"}
