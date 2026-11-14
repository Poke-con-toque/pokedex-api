"""Punto de entrada de la Pokédex API."""

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import settings
from app.database import create_db_and_tables
from app.limits import limiter
from app.logging_config import configurar_logging
from app.routers import auth, pokedex, pokemon, teams, v2

configurar_logging()
logger = logging.getLogger("pokedex_api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    logger.info("base de datos lista")
    yield
    logger.info("apagando")


app = FastAPI(
    title="Pokédex API",
    version="1.0.0",
    description="API REST del Pokédex personal · Práctica 1",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=3600,
)


def registrar_rate_limit(request: Request, exc: RateLimitExceeded):
    logger.warning(
        "Límite excedido: %s %s desde %s",
        request.method,
        request.url.path,
        request.client.host if request.client else "desconocido",
    )
    return _rate_limit_exceeded_handler(request, exc)


app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, registrar_rate_limit)
app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(RequestValidationError)
async def registrar_error_validacion(request: Request, exc: RequestValidationError):
    # No registramos los valores recibidos: podrían contener contraseñas u otros datos privados.
    errores = [{"loc": error.get("loc"), "type": error.get("type")} for error in exc.errors()]
    logger.warning(
        "Error de validación en %s %s: %s",
        request.method,
        request.url.path,
        errores,
    )
    return JSONResponse(
        status_code=422,
        content={"detail": jsonable_encoder(exc.errors())},
    )


@app.middleware("http")
async def registrar_peticiones(request: Request, call_next):
    inicio = time.perf_counter()
    respuesta = await call_next(request)
    ms = (time.perf_counter() - inicio) * 1000
    logger.info(
        "%s %s → %s (%.1f ms)",
        request.method,
        request.url.path,
        respuesta.status_code,
        ms,
    )
    return respuesta


for modulo in (auth, pokemon, pokedex, teams):
    app.include_router(modulo.router, prefix="/api/v1")

app.include_router(v2.router, prefix="/api/v2")


@app.get("/health", tags=["sistema"])
def health():
    return {"status": "ok"}
