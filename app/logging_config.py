"""Configuración común de logging para consola y archivo."""

import logging
from pathlib import Path

FORMATO = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
ARCHIVO_LOG = Path.cwd() / "pokedex_api.log"


def configurar_logging() -> None:
    """Configura una salida de consola y otra a pokedex_api.log sin duplicarlas."""
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    if not any(getattr(handler, "_pokedex_console", False) for handler in root.handlers):
        consola = logging.StreamHandler()
        consola.setFormatter(logging.Formatter(FORMATO))
        consola._pokedex_console = True
        root.addHandler(consola)
    if not any(getattr(handler, "_pokedex_file", False) for handler in root.handlers):
        archivo = logging.FileHandler(ARCHIVO_LOG, encoding="utf-8")
        archivo.setFormatter(logging.Formatter(FORMATO))
        archivo._pokedex_file = True
        root.addHandler(archivo)
