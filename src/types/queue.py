"""Queue type: FIFO queue backed by a doubly linked list."""

from typing import Generic, TypeVar

T = TypeVar("T")


class _Node(Generic[T]):
    """Internal doubly linked list node — not part of the public API."""

    __slots__ = ("value", "next")

    def __init__(self, value: T) -> None:
        self.value = value
        self.next: "_Node[T] | None" = None


class Queue(Generic[T]):
    """FIFO queue with O(1) enqueue/dequeue.

    Backed by a singly linked list with head/tail pointers (not a Python
    list), since a list's pop(0) is O(n). Used by bfs() as the traversal
    queue.
    """

    def __init__(self) -> None:
        self._head: _Node[T] | None = None
        self._tail: _Node[T] | None = None
        self._size = 0

    def __len__(self) -> int:
        """Return the number of elements currently in the queue."""
        return self._size

    def is_empty(self) -> bool:
        """Return True if the queue has no elements.

        Returns:
            True if empty, False otherwise.
        """
        return self._size == 0

    def enqueue(self, value: T) -> None:
        """Add value to the back of the queue.

        Args:
            value: Element to add.
        """
        node = _Node(value)
        if self._tail is None:
            self._head = self._tail = node
        else:
            self._tail.next = node
            self._tail = node
        self._size += 1

    def dequeue(self) -> T:
        """Remove and return the element at the front of the queue.

        Returns:
            The removed value.

        Raises:
            IndexError: If the queue is empty.
        """
        if self._head is None:
            raise IndexError("dequeue from an empty Queue")
        node = self._head
        self._head = node.next
        if self._head is None:
            self._tail = None
        self._size -= 1
        return node.value
