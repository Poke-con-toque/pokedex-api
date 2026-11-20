# Práctica 3 · Inspector recursivo de una planta industrial

- **Python:** 3.12+ (probado con 3.13). Solo biblioteca estándar.
- **Ejecutar la demo:** `cd starter` y `python inspector.py`
- **Ejecutar las pruebas** (desde `U03_inspector/`): `python -m unittest discover -s tests -v`

## Estructura

```
U03_inspector/
|-- README.md
|-- starter/
|   |-- inspector.py      # validate, preorden recursivo/iterativo, depth, count, find
|   |-- model.py          # Node y Record (inmutables, frozen=True)
|   `-- sample_data.py    # planta de ejemplo
`-- tests/
    `-- test_inspector.py # pruebas propias (23)
```

## Decisiones

1. **Funciones públicas + auxiliares recursivas.** Cada función pública (`maximum_depth`,
   `count_by_kind`...) llama primero a `validate` y después a una auxiliar privada (`_depth`,
   `_count`...) que hace la recursión. Así una entrada inválida falla con `ValueError` antes
   de dar resultados engañosos, y la recursión no repite la validación en cada nivel.
2. **Sin estado global.** El conjunto `seen` de nombres ya vistos se crea en cada llamada a
   `validate` y se pasa como parámetro. La única constante del módulo es una tupla (inmutable).
3. **Rutas con tuplas.** `path + (name,)` crea una tupla nueva, así cada llamada tiene su
   propia ruta y la del padre no cambia.
4. **Sin mutación.** El modelo es `frozen=True` y ninguna función modifica nodos (hay una
   prueba que compara el árbol con una copia profunda antes y después).
5. **Mensajes de error con ruta**, por ejemplo `P1/A1/S1: un sensor necesita valor numérico`.
6. **Decisión descartada:** obtener la profundidad, el recuento y la búsqueda a partir de la
   lista del preorden. El enunciado lo prohíbe y además cada función debe tener su propio caso
   base y su propia combinación.
7. No se exige que la raíz sea de tipo `plant`, porque el enunciado no lo pone como invariante
   obligatoria.

## Diagrama del árbol de ejemplo (`sample_data.py`)

```
P1 (plant)
|-- A1 (area)
|   `-- M1 (machine)
|       `-- T1 (sensor, 21.5)
`-- A2 (area)
    `-- PRES-1 (sensor, 3.2)
```

## Árbol parcial de llamadas: `_depth(P1)`

```
_depth(P1) = 1 + max(3, 2) = 4
|-- _depth(A1) = 1 + max(2) = 3
|   `-- _depth(M1) = 1 + max(1) = 2
|       `-- _depth(T1) = 1 + max(default 0) = 1   <- caso base (hoja)
`-- _depth(A2) = 1 + max(1) = 2
    `-- _depth(PRES-1) = 1                        <- caso base (hoja)
```

Las llamadas bajan hasta las hojas y los valores se combinan al volver (`1 + max(hijos)`).

## Funciones: caso base y combinación

| Función | Caso base | Paso recursivo | Combinación |
|---|---|---|---|
| `_validate_node` | hoja (sin hijos) | cada hijo con su ruta | ninguna (lanza error si falla) |
| `_preorder` | hoja: `[Record]` | cada hijo con `path` | concatenar listas |
| `_depth` | hoja: 1 | cada hijo | `1 + max` |
| `_count` | `{kind: 1}` | cada hijo | sumar diccionarios |
| `_find` | nombre igual: `(name,)`; hoja distinta: `None` | cada hijo en orden | anteponer `name` a la ruta encontrada |

## Pila implícita frente a pila explícita

**Recursiva (`_preorder`).** Cada llamada crea un *frame* en la pila de Python que guarda el
nodo, su ruta y en qué hijo va el bucle. Al terminar un hijo, Python vuelve al frame del padre
y sigue con el siguiente hijo. El código es muy parecido a la definición del árbol ("un nodo y
después sus hijos"), así que es fácil de leer y de comprobar. Si el árbol es muy profundo
(más de unos 1000 niveles, según `sys.getrecursionlimit()`) se produce `RecursionError`.

**Iterativa (`preorder_iterative`).** La lista `pending` hace el papel de la pila: guarda los
pares `(nodo, ruta)` que faltan por visitar. Se saca el último con `pop()`, se registra y sus
hijos se apilan **en orden inverso** (`reversed`) para que el primer hijo sea el siguiente en
salir y se mantenga el preorden. No depende del límite de recursión, porque la pila está en
memoria normal (heap), y se puede inspeccionar o limitar. A cambio, el código es un poco menos
directo.

**Equivalencia.** Las pruebas comparan las dos versiones con cuatro formas de árbol: solo la
raíz, lineal, ramificado y el de ejemplo. En todos los casos dan exactamente los mismos
`Record`.

**Coste** (n = número de nodos, h = altura, d = profundidad media de las rutas):

| Función | Tiempo | Espacio extra |
|---|---|---|
| `validate` | O(n·h) por construir las rutas; O(n) comprobaciones | O(n) del `seen` + O(h) de pila |
| `preorder_recursive` / `preorder_iterative` | O(n·d) (copiar las rutas) | O(h) de frames en la recursiva; en la iterativa la pila guarda los nodos pendientes (como máximo los hermanos de cada nivel de la rama actual) |
| `maximum_depth` | O(n) | O(h) |
| `count_by_kind` | O(n·k), con k = 4 tipos, es decir O(n) | O(h) |
| `find_path` | O(n) en el peor caso | O(h) |

## Evidencia de ejecución

```
$ cd starter && python inspector.py
Preorden recursivo:
  P1             plant    None
  P1/A1          area     None
  P1/A1/M1       machine  None
  P1/A1/M1/T1    sensor   21.5
  P1/A2          area     None
  P1/A2/PRES-1   sensor   3.2
Iterativo igual: True
Profundidad máxima: 4
Recuento por tipo: {'plant': 1, 'area': 2, 'machine': 1, 'sensor': 2}
Ruta de T1: ('P1', 'A1', 'M1', 'T1')
Ruta de X9: None
```

```
$ python -m unittest discover -s tests -v
...
Ran 23 tests in 0.002s

OK
```
