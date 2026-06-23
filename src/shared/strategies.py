"""Strategy pattern — CommunityDetectionStrategy.

Defines the abstract strategy and the swappable community-detection methods
compared in the final report (US14). Inject any of them into
``CommunityDetectionFilter`` to change algorithms without touching the filter.

The five methods of the comparison (see ``planning/questao_arestas_hierarquicas.md``
and ``docs/decisions.md``):

    1. ``ProgressiveEdgeCuttingStrategy`` — min-MST, hierarchical edges
       non-cuttable. The *baseline*: reproduces the ~700-node blob, which is the
       empirical evidence that structural containment must not *impose*
       membership. (Already implemented below.)
    2. ``RecalibratedHierarchyStrategy`` — min-MST, but hierarchical edges are
       reweighted *above* the relational scale so the minimum-MST stops
       preferring them; a word then joins the tree through a ``w_↔w_`` relation,
       not through containment. Minimal fix — the weight *influences*, not
       *imposes*.
    3. ``MaxSpanningTreeStrategy`` — per-type normalized weights + a *maximum*
       spanning tree (backbone = strongest similarities) + all edges cuttable.
       Principled fix.
    5. ``GreedyModularityStrategy`` — agglomerative greedy maximization of
       modularity Q (CNM-style), over the full graph.

Method 4 (detection restricted to the ``c_↔c_`` comment subgraph) is trivially
realizable by passing a pre-filtered subgraph to method 1/5 and is not a
separate strategy here.

**Status: strategies 2, 3, 5 are drafts.** The calibration constants
(``_HIERARCHY_RECALIBRATION_FACTOR``, ``_HIERARCHY_DAMPING_LAMBDA``) are
provisional and must be tuned empirically once the comparison runs with Q
(US12/US13). Wiring into ``community_detection.py``/``main.py`` is a later step.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable

from src.shared.graph import (
    add_edge,
    add_node,
    connected_components,
    copy_graph,
    count_components,
    get_edge_weight,
    has_edge,
    iter_edges,
    minimum_spanning_tree,
    neighbor_count,
    new_graph,
    remove_edge,
    total_edge_weight,
)
from src.types import Communities, Graph

_LEVEL_PREFIXES: tuple[str, ...] = ("w_", "s_", "c_")

# Provisional calibration — to be tuned once the 5-method comparison runs with Q
# (US12/US13). See planning/questao_arestas_hierarquicas.md ("Resolução").
_HIERARCHY_RECALIBRATION_FACTOR = 2.0  # method 2: hier. weight = factor x max relational weight
_HIERARCHY_DAMPING_LAMBDA = 0.5        # method 3: hier. influence in the normalized max-MST


def _level_of(node: str) -> str:
    """Return the level prefix (``"w_"``, ``"s_"``, ``"c_"``) of a node key.

    Args:
        node: Node key, e.g. ``"w_fps"`` or ``"s_12"``.

    Returns:
        The matching level prefix.

    Raises:
        ValueError: If node carries none of the known level prefixes.
    """
    for prefix in _LEVEL_PREFIXES:
        if node.startswith(prefix):
            return prefix
    raise ValueError(f"node {node!r} has no recognized level prefix")


def _is_relational(u: str, v: str) -> bool:
    """Return True if (u, v) links two nodes of the same level.

    Relational edges (``w_↔w_``, ``s_↔s_``, ``c_↔c_``) represent semantic
    similarity; cross-level edges are hierarchical (containment).

    Args:
        u: First node key.
        v: Second node key.

    Returns:
        True if both endpoints share the same level prefix.
    """
    return _level_of(u) == _level_of(v)


def _progressive_cut(
    tree: Graph, k: int, is_cuttable: Callable[[str, str], bool]
) -> Communities:
    """Cut a spanning tree's edges ascending by weight until k components.

    Shared cutting loop for the MST-based methods. Walks the tree's edges from
    weakest to strongest and removes each cuttable edge whose both endpoints
    still have degree > 1 (the guard protects leaf nodes from becoming
    singleton communities), stopping once ``k`` components exist.

    Args:
        tree: Spanning tree to cut. Mutated in place.
        k: Target number of communities.
        is_cuttable: Predicate ``(u, v) -> bool`` deciding whether an edge may
            be removed (e.g. ``_is_relational`` to spare hierarchical edges, or
            ``lambda u, v: True`` to allow every edge).

    Returns:
        Mapping of 1-indexed community id to its list of node keys.
    """
    sorted_edges = sorted(iter_edges(tree), key=lambda e: e[2])
    for u, v, _ in sorted_edges:
        if not has_edge(tree, u, v):
            continue
        if not is_cuttable(u, v):
            continue
        if neighbor_count(tree, u) > 1 and neighbor_count(tree, v) > 1:
            remove_edge(tree, u, v)
            if count_components(tree) >= k:
                break
    components = connected_components(tree)
    return {i + 1: component for i, component in enumerate(components)}


class CommunityDetectionStrategy(ABC):
    """Abstract strategy for graph community detection (Strategy pattern).

    Subclass this to provide an alternative partitioning algorithm.
    The default implementation is ``ProgressiveEdgeCuttingStrategy``.
    """

    @abstractmethod
    def detect(self, graph: Graph, k: int) -> Communities:
        """Partition graph nodes into at most k communities.

        Args:
            graph: Unified adjacency dict (final_graph.json format).
                   Must not be mutated — implementations must copy if needed.
            k: Target number of communities.

        Returns:
            Mapping of community_id (1-indexed int) to list of node keys.
        """


class ProgressiveEdgeCuttingStrategy(CommunityDetectionStrategy):
    """Default community detection: MST reduction + progressive edge cutting.

    Algorithm:
        1. Reduce the graph to a Minimum Spanning Tree (Prim) — V-1 edges.
        2. Sort the MST's edges ascending by weight.
        3. For each *relational* edge (u, v): if neighbor_count(u) > 1 and
           neighbor_count(v) > 1, remove it. Hierarchical (cross-level) edges are
           never cut, preserving the containment skeleton inside each community.
        4. After each removal, count connected components via BFS.
        5. Stop when components >= k or no more removable edges remain.

    The input graph is never mutated; ``copy_graph`` is called before
    building the MST. All traversal and MST construction is delegated to
    ``src.shared.graph``.
    """

    def detect(self, graph: Graph, k: int) -> Communities:
        """Partition graph into k communities by progressive edge cutting.

        Args:
            graph: Unified graph adjacency dict. Not mutated.
            k: Target number of communities to detect.

        Returns:
            Mapping of community_id (1-indexed) to list of node keys.
        """
        working = minimum_spanning_tree(copy_graph(graph))
        return _progressive_cut(working, k, is_cuttable=_is_relational)


def _recalibrate_hierarchical(graph: Graph, factor: float) -> Graph:
    """Return a copy where hierarchical edges weigh above the relational scale.

    Method 2's core transform. Every hierarchical (cross-level) edge is set to
    ``factor x (max relational weight)``, so that in a *minimum* spanning tree
    the cheap relational edges are preferred and a word joins the tree through a
    ``w_↔w_`` relation instead of through its containment edge. Relational edges
    keep their original weights.

    Args:
        graph: Final graph. Not mutated.
        factor: Multiplier (>= 1) applied to the max relational weight to obtain
            the uniform hierarchical weight.

    Returns:
        A new graph with hierarchical edges reweighted.
    """
    working = copy_graph(graph)
    edges = list(iter_edges(working))
    relational_max = max(
        (w for u, v, w in edges if _is_relational(u, v)), default=1.0
    )
    target = relational_max * factor
    for u, v, _ in edges:
        if not _is_relational(u, v):
            add_edge(working, u, v, target)
    return working


def _normalize_per_type(graph: Graph, hierarchical_lambda: float) -> Graph:
    """Return a copy with weights normalized to (0, 1] per edge type.

    Method 3's core transform. The three relational levels (``w_``/``s_``/``c_``)
    and the hierarchical edges live on very different magnitude scales; dividing
    each edge by the maximum weight of its own type makes them comparable.
    Hierarchical edges are additionally scaled by ``hierarchical_lambda`` so
    their influence on the maximum spanning tree can be damped (< 1) without
    being removed.

    Args:
        graph: Final graph. Not mutated.
        hierarchical_lambda: Factor in (0, 1] damping hierarchical influence.

    Returns:
        A new graph with per-type normalized weights, all strictly positive.
    """
    working = copy_graph(graph)
    edges = list(iter_edges(working))
    maxima: dict[str, float] = {}
    for u, v, w in edges:
        key = _level_of(u) if _is_relational(u, v) else "hier"
        maxima[key] = max(maxima.get(key, 0.0), w)
    for u, v, w in edges:
        if _is_relational(u, v):
            add_edge(working, u, v, w / maxima[_level_of(u)])
        else:
            add_edge(working, u, v, (w / maxima["hier"]) * hierarchical_lambda)
    return working


def _maximum_spanning_tree(graph: Graph) -> Graph:
    """Return a maximum spanning tree, reusing the from-scratch min-MST.

    Inverts each existing edge weight to ``(max_weight + 1) - w`` so the
    strongest original edges become the lightest, runs Prim's minimum spanning
    tree on the inverted graph, then restores the original weights on the
    surviving tree edges. The ``+ 1`` shift keeps every inverted weight strictly
    positive (never the ``0.0`` "no edge" sentinel). Non-edges stay ``0.0`` and
    are never inverted, so they remain absent.

    Args:
        graph: Graph to span. Not mutated.

    Returns:
        A new graph: a maximum spanning tree carrying original weights.
    """
    inverted = copy_graph(graph)
    edges = list(iter_edges(inverted))
    shift = max((w for _, _, w in edges), default=0.0) + 1.0
    for u, v, w in edges:
        add_edge(inverted, u, v, shift - w)
    tree = minimum_spanning_tree(inverted)
    for u, v, _ in list(iter_edges(tree)):
        add_edge(tree, u, v, shift - get_edge_weight(tree, u, v))
    return tree


class RecalibratedHierarchyStrategy(CommunityDetectionStrategy):
    """Method 2 (draft): min-MST with hierarchical edges reweighted to influence.

    Identical to the baseline (``ProgressiveEdgeCuttingStrategy``) except that
    hierarchical edges are first lifted above the relational weight scale
    (``_recalibrate_hierarchical``). In the resulting minimum spanning tree a
    word attaches through its strongest ``w_↔w_`` relation rather than through
    its (now expensive) containment edge, so containment *influences* membership
    instead of *imposing* it. Hierarchical edges remain non-cuttable, preserving
    the structural skeleton inside each community.
    """

    def __init__(self, factor: float = _HIERARCHY_RECALIBRATION_FACTOR) -> None:
        """Store the recalibration factor.

        Args:
            factor: Multiplier applied to the max relational weight to set the
                uniform hierarchical weight. Defaults to the provisional module
                constant.
        """
        self.factor = factor

    def detect(self, graph: Graph, k: int) -> Communities:
        """Partition the graph after lifting hierarchical edge weights.

        Args:
            graph: Unified final graph. Not mutated.
            k: Target number of communities.

        Returns:
            Mapping of 1-indexed community id to list of node keys.
        """
        recalibrated = _recalibrate_hierarchical(graph, self.factor)
        tree = minimum_spanning_tree(recalibrated)
        return _progressive_cut(tree, k, is_cuttable=_is_relational)


class MaxSpanningTreeStrategy(CommunityDetectionStrategy):
    """Method 3 (draft): max spanning tree on per-type normalized weights.

    Normalizes every edge to (0, 1] within its own type so the three relational
    levels and the (damped) hierarchical edges are comparable, builds a *maximum*
    spanning tree — whose backbone is therefore the strongest similarities, not
    the weakest as in the minimum-MST baseline — and then cuts every edge from
    weakest to strongest. Hierarchical edges are cuttable here, so a word may
    leave its sentence's community when similarity disagrees with containment.
    """

    def __init__(self, hierarchical_lambda: float = _HIERARCHY_DAMPING_LAMBDA) -> None:
        """Store the hierarchical damping factor.

        Args:
            hierarchical_lambda: Factor in (0, 1] scaling hierarchical influence
                in the normalized graph. Defaults to the provisional constant.
        """
        self.hierarchical_lambda = hierarchical_lambda

    def detect(self, graph: Graph, k: int) -> Communities:
        """Partition the graph via a max spanning tree of normalized weights.

        Args:
            graph: Unified final graph. Not mutated.
            k: Target number of communities.

        Returns:
            Mapping of 1-indexed community id to list of node keys.
        """
        normalized = _normalize_per_type(graph, self.hierarchical_lambda)
        tree = _maximum_spanning_tree(normalized)
        return _progressive_cut(tree, k, is_cuttable=lambda u, v: True)


class GreedyModularityStrategy(CommunityDetectionStrategy):
    """Method 5 (draft): agglomerative greedy modularity (Q) maximization.

    CNM-style bottom-up clustering: every node starts as its own community and
    the pair of communities whose merge yields the largest positive modularity
    gain is merged repeatedly. Only adjacent communities can raise Q, so the
    search ranges over the current cross-community edge weights.

    The merge gain uses the standard undirected-weighted form
    ``ΔQ = 2 (W_ab/2m - D_a·D_b/(2m)^2)``, where ``W_ab`` is the total weight of
    edges between communities a and b, ``D_i`` the summed weighted degree of
    community i, and ``2m`` the total weighted degree. Merging stops at exactly
    ``k`` communities, or earlier at the modularity peak if no merge improves Q
    (in which case the result may have more than ``k`` communities — that
    natural count is itself a comparison signal for the report).
    """

    def detect(self, graph: Graph, k: int) -> Communities:
        """Partition the graph by greedily maximizing modularity Q.

        Args:
            graph: Unified final graph. Not mutated (read-only access).
            k: Target number of communities (lower bound — see class docstring).

        Returns:
            Mapping of 1-indexed community id to list of node keys.
        """
        degree = {node: total_edge_weight(graph, node) for node in graph.nodes}
        m2 = sum(degree.values())  # == 2m
        if m2 == 0.0:
            return {i + 1: [node] for i, node in enumerate(graph.nodes)}

        # Each node is its own community; the representative key is the node name.
        members: dict[str, set[str]] = {node: {node} for node in graph.nodes}
        comm_degree: dict[str, float] = dict(degree)
        between: dict[frozenset[str], float] = {}
        for u, v, w in iter_edges(graph):
            key = frozenset((u, v))
            between[key] = between.get(key, 0.0) + w

        def delta_q(a: str, b: str) -> float:
            """Modularity gain of merging communities a and b."""
            w_ab = between.get(frozenset((a, b)), 0.0)
            return 2.0 * (w_ab / m2 - (comm_degree[a] * comm_degree[b]) / (m2 * m2))

        active = set(members)
        while len(active) > k:
            best_pair: tuple[str, str] | None = None
            best_gain = 0.0
            for pair in between:
                a, b = tuple(pair)
                gain = delta_q(a, b)
                if gain > best_gain:
                    best_gain = gain
                    best_pair = (a, b)
            if best_pair is None:
                break  # no merge improves Q — stop at the modularity peak
            a, b = best_pair
            members[a] |= members[b]
            comm_degree[a] += comm_degree[b]
            active.discard(b)
            # Redirect b's cross-community weights onto a; drop the a–b link.
            for pair in [key for key in between if b in key]:
                weight = between.pop(pair)
                other = next(iter(pair - {b}))
                if other == a:
                    continue  # becomes internal to the merged community
                merged_key = frozenset((a, other))
                between[merged_key] = between.get(merged_key, 0.0) + weight

        return {
            i + 1: sorted(members[comm]) for i, comm in enumerate(active)
        }


def _comment_subgraph(graph: Graph) -> Graph:
    """Return the relational subgraph induced by the comment nodes (``c_``).

    Method 4's core transform. Keeps only ``c_`` nodes and the ``c_↔c_``
    relational edges between them; every word and sentence node — and every
    hierarchical edge — is dropped. Partitioning this subgraph therefore ignores
    the word/sentence "blob" entirely and clusters comments purely by their
    mutual similarity.

    Args:
        graph: Final graph. Not mutated.

    Returns:
        A new graph over the comment nodes only, carrying the original
        ``c_↔c_`` edge weights. Comment nodes with no relational edge are kept
        as isolated nodes so the partition still covers every comment.
    """
    subgraph = new_graph()
    for node in graph.nodes:
        if node.startswith("c_"):
            add_node(subgraph, node)
    for u, v, weight in iter_edges(graph):
        if u.startswith("c_") and v.startswith("c_"):
            add_edge(subgraph, u, v, weight)
    return subgraph


class CommentSubgraphStrategy(CommunityDetectionStrategy):
    """Method 4: progressive edge cutting restricted to the ``c_↔c_`` subgraph.

    Extracts the comment-only subgraph (``_comment_subgraph``) and runs the same
    minimum-MST progressive cut as the baseline on it, so the word/sentence blob
    that dominates the full-graph methods is sidestepped entirely. The resulting
    communities contain comment nodes only; words/sentences are intentionally
    out of scope for this method.

    Because the subgraph may be disconnected (comments with no mutual
    similarity), its minimum spanning *forest* already yields one component per
    connected piece; the progressive cut then refines the largest pieces toward
    ``k``. Every comment is covered, isolated ones forming their own community.
    """

    def detect(self, graph: Graph, k: int) -> Communities:
        """Partition the comment subgraph into communities.

        Args:
            graph: Unified final graph. Not mutated.
            k: Target number of communities.

        Returns:
            Mapping of 1-indexed community id to list of comment node keys.
        """
        subgraph = _comment_subgraph(graph)
        tree = minimum_spanning_tree(subgraph)
        # Every surviving edge is c_↔c_, hence relational — all are cuttable.
        return _progressive_cut(tree, k, is_cuttable=_is_relational)


# ── Method registry ───────────────────────────────────────────────────────────
# Single source of truth for the 5-method line-up compared in the final report
# (US14). ``analysis.py`` iterates this list to build the comparison matrix.
DETECTION_METHODS: list[dict[str, object]] = [
    {
        "id": 1,
        "label": "Corte progressivo na min-MST (baseline, hierárquicas não-cortáveis)",
        "strategy": ProgressiveEdgeCuttingStrategy(),
    },
    {
        "id": 2,
        "label": "Min-MST com peso hierárquico recalibrado",
        "strategy": RecalibratedHierarchyStrategy(),
    },
    {
        "id": 3,
        "label": "Max-MST sobre pesos normalizados por tipo",
        "strategy": MaxSpanningTreeStrategy(),
    },
    {
        "id": 4,
        "label": "Corte progressivo no subgrafo de comentários (c_↔c_)",
        "strategy": CommentSubgraphStrategy(),
    },
    {
        "id": 5,
        "label": "Maximização gulosa da modularidade Q",
        "strategy": GreedyModularityStrategy(),
    },
]
