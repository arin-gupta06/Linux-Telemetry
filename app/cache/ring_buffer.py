import threading
from collections import deque
from typing import Generic, List, Optional, TypeVar

T = TypeVar("T")


class ThreadSafeRingBuffer(Generic[T]):
    """Thread-safe ring buffer with fixed capacity and fast O(1) appends."""

    def __init__(self, capacity: int = 10_000):
        self.capacity = max(10, capacity)
        self._deque: deque[T] = deque(maxlen=self.capacity)
        self._lock = threading.RLock()
        self._total_appended = 0

    def append(self, item: T) -> None:
        with self._lock:
            self._deque.append(item)
            self._total_appended += 1

    def append_many(self, items: List[T]) -> None:
        with self._lock:
            self._deque.extend(items)
            self._total_appended += len(items)

    def get_all(self) -> List[T]:
        with self._lock:
            return list(self._deque)

    def get_recent(self, limit: int = 100) -> List[T]:
        with self._lock:
            if limit >= len(self._deque):
                return list(self._deque)
            return list(self._deque)[-limit:]

    def clear(self) -> None:
        with self._lock:
            self._deque.clear()

    def size(self) -> int:
        with self._lock:
            return len(self._deque)

    def total_appended(self) -> int:
        with self._lock:
            return self._total_appended
