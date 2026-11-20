"""Planta de ejemplo del enunciado."""

from model import Node


def sample_plant() -> Node:
    return Node(
        "P1",
        "plant",
        children=(
            Node("A1", "area", children=(
                Node("M1", "machine", children=(
                    Node("T1", "sensor", 21.5),
                )),
            )),
            Node("A2", "area", children=(
                Node("PRES-1", "sensor", 3.2),
            )),
        ),
    )
