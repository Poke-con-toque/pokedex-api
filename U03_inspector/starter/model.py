"""Modelo inmutable de la planta (proporcionado por el enunciado)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Node:
    name: str
    kind: str
    value: float | None = None
    children: tuple["Node", ...] = ()


@dataclass(frozen=True)
class Record:
    path: tuple[str, ...]
    kind: str
    value: float | None
