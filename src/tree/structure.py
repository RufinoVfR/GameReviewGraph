"""N-ary tree data structure: ``TreeNode`` + ``NaryTree``.

Models the textual hierarchy Dataset -> Comment -> Sentence -> Word. Each node
carries a ``data`` dict (its domain payload, including a ``"type"`` tag), a
back-reference to its ``parent``, and an ordered list of ``children`` — giving
the bidirectional navigation required by US04. Built with native Python types
only; no external tree/graph library is involved.

The navigation accessors here operate on the live ``NaryTree`` and are the US04
deliverable, exercised by this package's own unit tests. They are **not** a
cross-filter API: downstream graph filters read ``tree.json`` as a plain dict
through ``src/shared/tree.py`` instead of rebuilding a ``NaryTree``.
"""


class TreeNode:
    """A single node of the N-ary tree.

    Attributes:
        data: Domain payload, always containing a ``"type"`` key
            (``"dataset"`` | ``"comment"`` | ``"sentence"`` | ``"word"``) plus the
            level-specific fields (``id`` / ``index`` / ``value`` + ``position``).
        parent: The parent node, or ``None`` for the root.
        children: Ordered child nodes (always empty for ``word`` leaves).
    """

    def __init__(self, data: dict, parent: "TreeNode | None" = None) -> None:
        """Create a node from its payload and optional parent.

        Args:
            data: Domain payload dict (must contain a ``"type"`` key).
            parent: Parent node, or ``None`` for the root.
        """
        self.data = data
        self.parent = parent
        self.children: list[TreeNode] = []


class NaryTree:
    """N-ary tree over the textual hierarchy, with bidirectional navigation.

    Attributes:
        root: The ``dataset`` node at the top of the hierarchy.
    """

    def __init__(self, root: TreeNode) -> None:
        """Wrap an existing root node.

        Args:
            root: The ``dataset`` node that anchors the tree.
        """
        self.root = root

    def add_child(self, parent_node: TreeNode, child_data: dict) -> TreeNode:
        """Create a child of ``parent_node`` and wire the bidirectional link.

        Sets the child's ``parent`` back-reference and appends it to the
        parent's ``children`` in a single place, so the two directions can never
        drift apart.

        Args:
            parent_node: Node that will own the new child.
            child_data: Domain payload for the child node.

        Returns:
            The newly created child node.
        """
        child = TreeNode(child_data, parent=parent_node)
        parent_node.children.append(child)
        return child

    def get_words_of_sentence(self, sentence_node: TreeNode) -> list[TreeNode]:
        """Return the word nodes of a sentence, in reading order.

        Args:
            sentence_node: A ``sentence`` node.

        Returns:
            The sentence's ``word`` children (empty if the sentence has none).
        """
        return list(sentence_node.children)

    def get_sentences_of_comment(self, comment_node: TreeNode) -> list[TreeNode]:
        """Return the sentence nodes of a comment, in order.

        Args:
            comment_node: A ``comment`` node.

        Returns:
            The comment's ``sentence`` children (empty if the comment has none).
        """
        return list(comment_node.children)

    def get_all_word_nodes(self) -> list[TreeNode]:
        """Collect every ``word`` node in the tree via depth-first traversal.

        Returns:
            All word-level nodes, in document order.
        """
        words: list[TreeNode] = []
        stack: list[TreeNode] = [self.root]
        while stack:
            node = stack.pop()
            if node.data.get("type") == "word":
                words.append(node)
            # Reverse so children are visited left-to-right (document order).
            stack.extend(reversed(node.children))
        return words
