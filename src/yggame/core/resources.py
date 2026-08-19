# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Explicit resource ownership and scoped cleanup utilities."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from .errors import LifecycleError

T = TypeVar("T")


@dataclass(slots=True)
class ResourceEntry(Generic[T]):
    key: str
    value: T
    disposer: Callable[[T], None] | None = None
    references: int = 0


class ResourceHandle(Generic[T]):
    """Reference-counted handle that releases its resource exactly once."""

    __slots__ = ("_manager", "_key", "_value", "_released")

    def __init__(self, manager: ResourceManager, key: str, value: T) -> None:
        self._manager = manager
        self._key = key
        self._value = value
        self._released = False

    @property
    def value(self) -> T:
        if self._released:
            raise LifecycleError("resource handle has already been released")
        return self._value

    @property
    def released(self) -> bool:
        return self._released

    def release(self) -> None:
        if not self._released:
            self._released = True
            self._manager.release(self._key)

    def __enter__(self) -> T:
        return self.value

    def __exit__(self, *_: object) -> None:
        self.release()

    def __del__(self) -> None:
        self.release()


class ResourceManager:
    """Loads and owns resources by stable string keys.

    Loading is synchronous by design at this layer. Async/background loading can be
    built above the same acquire/release contract without weakening ownership rules.
    """

    def __init__(self) -> None:
        self._entries: dict[str, ResourceEntry[Any]] = {}
        self._scopes: list[set[str]] = []

    def acquire(
        self, key: str, loader: Callable[[], T], *, disposer: Callable[[T], None] | None = None
    ) -> ResourceHandle[T]:
        if not key:
            raise ValueError("resource key cannot be empty")
        entry = self._entries.get(key)
        if entry is None:
            entry = ResourceEntry(key, loader(), disposer, 0)
            self._entries[key] = entry
        elif disposer is not None and entry.disposer is None:
            entry.disposer = disposer
        entry.references += 1
        if self._scopes:
            self._scopes[-1].add(key)
        return ResourceHandle(self, key, entry.value)

    def release(self, key: str) -> None:
        entry = self._entries.get(key)
        if entry is None:
            raise KeyError(f"unknown resource: {key}")
        entry.references -= 1
        if entry.references < 0:
            raise LifecycleError(f"resource released too many times: {key}")
        if entry.references == 0:
            if entry.disposer:
                entry.disposer(entry.value)
            self._entries.pop(key, None)

    def get(self, key: str) -> Any:
        try:
            return self._entries[key].value
        except KeyError as exc:
            raise KeyError(f"resource is not loaded: {key}") from exc

    def loaded(self, key: str) -> bool:
        return key in self._entries

    @contextmanager
    def scope(self) -> Iterator[ResourceManager]:
        owned: set[str] = set()
        self._scopes.append(owned)
        try:
            yield self
        finally:
            self._scopes.pop()
            for key in reversed(tuple(owned)):
                if key in self._entries:
                    self.release(key)

    def clear(self) -> None:
        for key in reversed(tuple(self._entries)):
            entry = self._entries[key]
            if entry.disposer:
                entry.disposer(entry.value)
        self._entries.clear()
        self._scopes.clear()

    def keys(self) -> tuple[str, ...]:
        return tuple(sorted(self._entries))
