"""Limitador de peticiones, en su propio módulo para que los routers lo importen sin ciclos.

Los límites se cuentan por dirección IP y en memoria (se ponen a cero al reiniciar).
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Endpoints públicos de autenticación: los más estrictos, frenan la fuerza bruta y el spam.
LIMITE_REGISTRO = "5/hour"
LIMITE_LOGIN = "10/minute"
# Endpoints que llaman a la PokeAPI: cada petición nuestra genera otras hacia fuera.
LIMITE_POKEAPI = "30/minute"
# Resto de endpoints autenticados: sólo tocan nuestra base de datos.
LIMITE_GENERAL = "100/minute"

# Cada endpoint declara su límite con @limiter.limit. No usamos default_limits: con
# FastAPI ≥ 0.148 el middleware de slowapi no encuentra las rutas de los routers
# incluidos y esos límites por defecto no se aplicarían nunca (lo comprueban los tests).
limiter = Limiter(key_func=get_remote_address)
