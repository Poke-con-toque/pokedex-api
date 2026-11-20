"""Inspector recursivo de una planta industrial.

Todas las funciones son puras: no modifican el árbol y no usan estado global.
Las funciones de consulta validan primero el árbol, así una entrada inválida
falla con ValueError antes de producir resultados engañosos.
"""

from model import Node, Record

ALLOWED_KINDS = ("plant", "area", "machine", "sensor")  # tupla: inmutable


# ---------------------------------------------------------------- validación

def validate(root: Node) -> None:
    """Lanza ValueError si el árbol incumple alguna invariante."""
    _validate_node(root, (), set())


def _validate_node(node: Node, parent_path: tuple[str, ...], seen: set[str]) -> None:
    # 'seen' es local a cada llamada a validate(), no es una variable global.
    if not isinstance(node, Node):
        raise ValueError(f"{'/'.join(parent_path) or '<raíz>'}: hijo que no es Node: {node!r}")

    if not isinstance(node.name, str) or not node.name.strip():
        raise ValueError(f"{'/'.join(parent_path) or '<raíz>'}: nombre vacío o no textual: {node.name!r}")

    path = parent_path + (node.name,)
    where = "/".join(path)

    if node.name in seen:
        raise ValueError(f"{where}: nombre duplicado {node.name!r}")
    seen.add(node.name)

    if node.kind not in ALLOWED_KINDS:
        raise ValueError(f"{where}: tipo desconocido {node.kind!r}")

    if not isinstance(node.children, tuple):
        raise ValueError(f"{where}: children debe ser una tupla")

    if node.kind == "sensor":
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise ValueError(f"{where}: un sensor necesita valor numérico, recibido {node.value!r}")
        if node.children:
            raise ValueError(f"{where}: un sensor no puede tener hijos")
    elif node.value is not None:
        raise ValueError(f"{where}: un nodo {node.kind!r} no puede tener valor")

    # Caso base implícito: sin hijos el bucle no hace nada.
    for child in node.children:
        _validate_node(child, path, seen)


# ---------------------------------------------------------------- preorden

def preorder_recursive(root: Node) -> list[Record]:
    """Preorden con recursión estructural: raíz y después cada hijo en orden."""
    validate(root)
    return _preorder(root, ())


def _preorder(node: Node, parent_path: tuple[str, ...]) -> list[Record]:
    path = parent_path + (node.name,)          # tupla nueva, no se muta la anterior
    result = [Record(path, node.kind, node.value)]
    for child in node.children:                # caso base: hoja -> sin llamadas
        result.extend(_preorder(child, path))  # combinación: concatenar
    return result


def preorder_iterative(root: Node) -> list[Record]:
    """Preorden con pila explícita; no llama a la versión recursiva."""
    validate(root)
    result: list[Record] = []
    pending: list[tuple[Node, tuple[str, ...]]] = [(root, (root.name,))]
    while pending:
        node, path = pending.pop()
        result.append(Record(path, node.kind, node.value))
        # Se apilan al revés para que el primer hijo salga primero.
        for child in reversed(node.children):
            pending.append((child, path + (child.name,)))
    return result


# ---------------------------------------------------------------- consultas

def maximum_depth(root: Node) -> int:
    """Longitud de la ruta más profunda, raíz incluida (raíz sola = 1)."""
    validate(root)
    return _depth(root)


def _depth(node: Node) -> int:
    # Caso base: hoja -> max(..., default=0) + 1 = 1
    return 1 + max((_depth(child) for child in node.children), default=0)


def count_by_kind(root: Node) -> dict[str, int]:
    """Cantidad de nodos de cada tipo presente (orden de aparición en preorden)."""
    validate(root)
    return _count(root)


def _count(node: Node) -> dict[str, int]:
    counts = {node.kind: 1}                      # caso base: el propio nodo
    for child in node.children:
        for kind, amount in _count(child).items():   # combinar resultados de hijos
            counts[kind] = counts.get(kind, 0) + amount
    return counts


def find_path(root: Node, target: str) -> tuple[str, ...] | None:
    """Ruta desde la raíz hasta 'target' (primera en preorden) o None."""
    validate(root)
    return _find(root, target)


def _find(node: Node, target: str) -> tuple[str, ...] | None:
    if node.name == target:                      # caso base: encontrado
        return (node.name,)
    for child in node.children:
        found = _find(child, target)
        if found is not None:                    # propagar la solución
            return (node.name,) + found
    return None                                  # caso base: no está en este subárbol


# ---------------------------------------------------------------- demo

if __name__ == "__main__":
    from sample_data import sample_plant

    plant = sample_plant()
    print("Preorden recursivo:")
    for record in preorder_recursive(plant):
        print(f"  {'/'.join(record.path):<14} {record.kind:<8} {record.value}")
    print("Iterativo igual:", preorder_iterative(plant) == preorder_recursive(plant))
    print("Profundidad máxima:", maximum_depth(plant))
    print("Recuento por tipo:", count_by_kind(plant))
    print("Ruta de T1:", find_path(plant, "T1"))
    print("Ruta de X9:", find_path(plant, "X9"))
