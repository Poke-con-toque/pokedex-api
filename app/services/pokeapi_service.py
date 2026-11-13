"""Cliente de la PokeAPI: llama fuera, traduce los errores y simplifica la respuesta."""

import logging
import re
import time

import httpx
from fastapi import HTTPException, status

from app.services.pokeapi_fallback import POKEMON_DE_RESERVA

logger = logging.getLogger("pokedex_api.pokeapi")

# Nombres de la PokeAPI: minúsculas, números y guiones (mr-mime, porygon-z…).
NOMBRE_VALIDO = re.compile(r"^[a-z0-9-]{1,50}$")

# Caché compartida por todas las instancias del servicio (se crea una por petición).
# Los datos de un Pokémon no cambian, así que guardar la respuesta es seguro.
_cache: dict[str, dict] = {}
CACHE_MAX = 512


def limpiar_cache() -> None:
    _cache.clear()


class PokeAPIService:
    def __init__(
        self, base_url: str, timeout: float = 5.0, usar_reserva: bool = False
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        # Si la PokeAPI está caída, responde con datos de reserva (FAQ del enunciado).
        self.usar_reserva = usar_reserva

    # ─────────────────────────── API pública ───────────────────────────

    async def get_pokemon(self, identificador: int | str) -> dict:
        """Ficha simplificada de un Pokémon por id o nombre."""
        clave = self._validar_identificador(identificador)
        try:
            bruto = await self._get(
                f"/pokemon/{clave}", no_existe=f"No existe el Pokémon {identificador}"
            )
        except HTTPException as error:
            if error.status_code in (502, 504) and self.usar_reserva:
                reserva = self._reserva(clave)
                if reserva is not None:
                    logger.warning("PokeAPI caída: uso datos de reserva para %s", clave)
                    return reserva
            raise
        return self._simplificar(bruto)

    async def search_pokemon(self, limit: int = 20, offset: int = 0) -> dict:
        """Lista paginada de Pokémon: {count, results: [{id, name}]}."""
        if not 1 <= limit <= 2000 or offset < 0:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                "limit debe estar entre 1 y 2000 y offset ser mayor o igual que 0",
            )
        bruto = await self._get(
            f"/pokemon?limit={limit}&offset={offset}", no_existe="Página no encontrada"
        )
        return {
            "count": bruto["count"],
            "results": [
                {"id": self._id_de_url(p["url"]), "name": p["name"]}
                for p in bruto["results"]
            ],
        }

    async def get_pokemon_by_type(self, type_name: str) -> list[dict]:
        """Todos los Pokémon de un tipo: [{id, name}]."""
        tipo = self._validar_identificador(type_name)
        bruto = await self._get(f"/type/{tipo}", no_existe=f"No existe el tipo {type_name}")
        return [
            {"id": self._id_de_url(p["pokemon"]["url"]), "name": p["pokemon"]["name"]}
            for p in bruto["pokemon"]
        ]

    async def get_pokemon_species(self, identificador: int | str) -> dict:
        """Datos de la especie: descripción (en español si existe), categoría y evolución."""
        clave = self._validar_identificador(identificador)
        bruto = await self._get(
            f"/pokemon-species/{clave}",
            no_existe=f"No existe la especie {identificador}",
        )
        return {
            "id": bruto["id"],
            "name": bruto["name"],
            "description": self._en_idioma(bruto.get("flavor_text_entries", []), "flavor_text"),
            "genus": self._en_idioma(bruto.get("genera", []), "genus"),
            "evolution_chain_url": (bruto.get("evolution_chain") or {}).get("url"),
        }

    async def get_evolution_chain(self, url: str) -> list[str]:
        """Nombres de la cadena evolutiva en orden: ['bulbasaur', 'ivysaur', 'venusaur']."""
        ruta = url.removeprefix(self.base_url)
        bruto = await self._get(ruta, no_existe="No existe la cadena evolutiva")
        nombres: list[str] = []
        pendientes = [bruto["chain"]]
        while pendientes:
            eslabon = pendientes.pop(0)
            nombres.append(eslabon["species"]["name"])
            pendientes.extend(eslabon.get("evolves_to", []))
        return nombres

    # ─────────────────────────── Internos ───────────────────────────

    async def _get(self, ruta: str, no_existe: str) -> dict:
        url = f"{self.base_url}{ruta}"
        if url in _cache:
            logger.info("PokeAPI GET %s → caché", url)
            return _cache[url]

        inicio = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as cliente:
                respuesta = await cliente.get(url)
        except httpx.TimeoutException:
            logger.error("PokeAPI GET %s → timeout tras %.1f s", url, self.timeout)
            raise HTTPException(status.HTTP_504_GATEWAY_TIMEOUT, "PokeAPI no responde")
        except httpx.HTTPError as error:
            logger.error("PokeAPI GET %s → error de red: %s", url, error)
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, "PokeAPI no disponible")

        ms = (time.perf_counter() - inicio) * 1000
        logger.info("PokeAPI GET %s → %s (%.1f ms)", url, respuesta.status_code, ms)

        if respuesta.status_code == 404:
            raise HTTPException(status.HTTP_404_NOT_FOUND, no_existe)
        if respuesta.is_error:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, "PokeAPI no disponible")

        datos = respuesta.json()
        if len(_cache) >= CACHE_MAX:
            _cache.pop(next(iter(_cache)))  # sale la entrada más antigua
        _cache[url] = datos
        return datos

    @staticmethod
    def _validar_identificador(identificador: int | str) -> str:
        clave = str(identificador).strip().lower()
        if clave.isdigit():
            if int(clave) < 1:
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_CONTENT, "El id debe ser mayor que 0"
                )
            return str(int(clave))
        if not NOMBRE_VALIDO.match(clave):
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                f"Identificador no válido: {identificador}",
            )
        return clave

    @staticmethod
    def _reserva(clave: str) -> dict | None:
        for pokemon in POKEMON_DE_RESERVA:
            if clave in (str(pokemon["id"]), pokemon["name"]):
                return pokemon
        return None

    @staticmethod
    def _id_de_url(url: str) -> int:
        # https://pokeapi.co/api/v2/pokemon/25/ → 25
        return int(url.rstrip("/").rsplit("/", 1)[-1])

    @staticmethod
    def _en_idioma(entradas: list[dict], campo: str) -> str | None:
        for idioma in ("es", "en"):
            for entrada in entradas:
                if entrada["language"]["name"] == idioma:
                    # Los textos de la PokeAPI traen saltos de línea y de página sueltos.
                    return " ".join(entrada[campo].split())
        return None

    @staticmethod
    def _simplificar(bruto: dict) -> dict:
        # La frontera del sistema: lo ajeno entra aquí y sale con nuestro vocabulario.
        stats = {s["stat"]["name"]: s["base_stat"] for s in bruto.get("stats", [])}
        sprites = bruto.get("sprites") or {}
        return {
            "id": bruto["id"],
            "name": bruto["name"],
            "sprite": sprites.get("front_default"),
            "types": [t["type"]["name"] for t in bruto.get("types", [])],
            "stats": {
                clave: stats.get(clave)
                for clave in ("hp", "attack", "defense", "speed")
            },
            "abilities": [a["ability"]["name"] for a in bruto.get("abilities", [])],
            "sprites": {
                "front_default": sprites.get("front_default"),
                "back_default": sprites.get("back_default"),
                "front_shiny": sprites.get("front_shiny"),
                "official_artwork": (
                    (sprites.get("other") or {})
                    .get("official-artwork", {})
                    .get("front_default")
                ),
            },
            "height": bruto.get("height"),
            "weight": bruto.get("weight"),
        }
