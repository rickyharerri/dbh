"""Tiny thread-safe TTL + LRU cache. Warehouse round-trips are the slow part of this app."""
from __future__ import annotations

import threading
import time
from collections import OrderedDict
from typing import Any, Callable, Hashable


class TTLCache:
    def __init__(self, ttl_seconds: int, max_entries: int = 256):
        self.ttl = ttl_seconds
        self.max = max_entries
        self._data: "OrderedDict[Hashable, tuple[float, Any]]" = OrderedDict()
        self._lock = threading.Lock()

    def get_or_set(self, key: Hashable, factory: Callable[[], Any]) -> Any:
        if self.ttl <= 0:
            return factory()
        now = time.monotonic()
        with self._lock:
            hit = self._data.get(key)
            if hit and now - hit[0] < self.ttl:
                self._data.move_to_end(key)
                return hit[1]
        value = factory()  # computed outside the lock so slow queries don't block other keys
        with self._lock:
            self._data[key] = (time.monotonic(), value)
            self._data.move_to_end(key)
            while len(self._data) > self.max:
                self._data.popitem(last=False)
        return value

    def clear(self) -> None:
        with self._lock:
            self._data.clear()
