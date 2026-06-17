"""``tree.json`` (de)serialization: ``NaryTree`` <-> uniform-node nested dict.

The on-disk format is the closed contract from ``docs/guia_implementacao.md``
(C.1): a uniform node ``{"type", "children", ...}`` where ``word`` leaves carry
``value`` + ``position``, ``sentence`` carries a global ``index``, and
``comment`` carries its ``id``. No ``w_``/``s_``/``c_`` prefixes are stored — the
graph filters apply those when they read the artifact.

``serialize`` is the filter's production output. ``from_dict`` is test-only:
nothing on the production path rebuilds a ``NaryTree`` (downstream filters walk
the dict via ``src/shared/tree.py``); it exists for the round-trip test.
"""

from src.tree.structure import NaryTree, TreeNode


def serialize(tree: NaryTree) -> dict:
    """Serialize the tree to the uniform-node nested dict (``tree.json``).

    The result is acyclic: ``parent`` back-references are not emitted, only the
    nested ``children``. ``word`` leaves are emitted without a ``children`` key;
    every other level always carries ``children`` (possibly empty).

    Args:
        tree: The N-ary tree to serialize.

    Returns:
        A JSON-serializable nested dict rooted at the ``dataset`` node.
    """
    return _node_to_dict(tree.root)


def _node_to_dict(node: TreeNode) -> dict:
    """Recursively convert a node and its subtree to the uniform-node dict.

    Args:
        node: The node to convert.

    Returns:
        A dict copy of ``node.data``, plus a ``children`` list for every
        non-``word`` node.
    """
    data = dict(node.data)
    if node.data.get("type") != "word":
        data["children"] = [_node_to_dict(child) for child in node.children]
    return data


def from_dict(data: dict) -> NaryTree:
    """Rebuild a ``NaryTree`` from a serialized dict, re-linking parents.

    Test-only counterpart of :func:`serialize`; the production pipeline never
    deserializes the tree into objects.

    Args:
        data: A uniform-node nested dict (the ``tree.json`` shape).

    Returns:
        The reconstructed ``NaryTree`` with ``parent`` back-references restored.
    """
    return NaryTree(_dict_to_node(data, parent=None))


def _dict_to_node(data: dict, parent: TreeNode | None) -> TreeNode:
    """Recursively rebuild a node and its subtree, wiring parents on descent.

    Args:
        data: The serialized node dict.
        parent: The already-built parent node, or ``None`` for the root.

    Returns:
        The rebuilt node with its children attached and parents linked.
    """
    payload = {key: value for key, value in data.items() if key != "children"}
    node = TreeNode(payload, parent=parent)
    node.children = [_dict_to_node(child, parent=node) for child in data.get("children", [])]
    return node
