# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Reusable object pool for high-frequency gameplay allocations."""

from __future__ import annotations

from collections.abc import Callable
from typing import Generic, TypeVar

T = TypeVar("T")


class ObjectPool(Generic[T]):
    """Pool objects created by a factory and optionally reset on release.

    The pool never silently grows beyond `max_size`; callers receive a clear
    `PoolExhausted` error so they can choose to drop, queue, or allocate elsewhere.
    """

    def __init__(
        self,
        factory: Callable[[], T],
        *,
        initial_size: int = 0,
        max_size: int | None = None,
        reset: Callable[[T], None] | None = None,
    ) -> None:
        if initial_size < 0 or (max_size is not None and max_size <= 0):
            raise ValueError("pool sizes must be non-negative and max_size positive")
        if max_size is not None and initial_size > max_size:
            raise ValueError("initial_size cannot exceed max_size")
        self.factory = factory
        self.max_size = max_size
        self.reset = reset
        self._free: list[T] = []
        self._active: set[int] = set()
        self._objects: dict[int, T] = {}
        for _ in range(initial_size):
            item = factory()
            self._free.append(item)
            self._objects[id(item)] = item

    @property
    def active_count(self) -> int:
        return len(self._active)

    @property
    def free_count(self) -> int:
        return len(self._free)

    @property
    def size(self) -> int:
        return len(self._objects)

    def acquire(self) -> T:
        if self._free:
            item = self._free.pop()
        else:
            if self.max_size is not None and len(self._objects) >= self.max_size:
                raise PoolExhausted("object pool reached its configured max_size")
            item = self.factory()
            self._objects[id(item)] = item
        self._active.add(id(item))
        return item

    def release(self, item: T) -> None:
        key = id(item)
        if key not in self._active:
            raise ValueError("cannot release an object that is not active in this pool")
        self._active.remove(key)
        if self.reset:
            self.reset(item)
        self._free.append(item)

    def clear(self, *, dispose: Callable[[T], None] | None = None) -> None:
        if self._active:
            raise RuntimeError("cannot clear a pool while objects are active")
        if dispose:
            for item in self._objects.values():
                dispose(item)
        self._free.clear()
        self._objects.clear()


class PoolExhausted(RuntimeError):
    """Raised when an object pool has no available capacity."""
