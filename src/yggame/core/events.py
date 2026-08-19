# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Typed event records and a safe, deterministic publish/subscribe bus."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from inspect import iscoroutinefunction
from threading import RLock
from time import monotonic
from typing import Any, TypeVar

EventHandler = Callable[["Event"], Any]
T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class Event:
    """An immutable event delivered to subscribers.

    `name` is intentionally a string to keep plugins decoupled. The payload should
    contain serializable values when events may be recorded or sent over a network.
    """

    name: str
    payload: Any = None
    source: Any = None
    timestamp: float = field(default_factory=monotonic)
    bubbles: bool = True

    def get(self, key: str, default: T | None = None) -> Any | T | None:
        if isinstance(self.payload, dict):
            return self.payload.get(key, default)
        return default


@dataclass(slots=True)
class _Subscription:
    token: int
    callback: EventHandler
    priority: int
    once: bool


class Subscription:
    """Cancellable handle returned by `EventBus.subscribe`."""

    __slots__ = ("_bus", "_name", "_token", "_cancelled")

    def __init__(self, bus: EventBus, name: str, token: int) -> None:
        self._bus, self._name, self._token = bus, name, token
        self._cancelled = False

    @property
    def cancelled(self) -> bool:
        return self._cancelled

    def cancel(self) -> None:
        if not self._cancelled:
            self._bus.unsubscribe(self._name, self._token)
            self._cancelled = True

    def __enter__(self) -> Subscription:
        return self

    def __exit__(self, *_: object) -> None:
        self.cancel()


class EventBus:
    """Synchronous event bus with safe mutation during dispatch.

    Handlers are called from highest priority to lowest priority. Returning `False`
    stops propagation. Async handlers are rejected explicitly because silently
    creating un-awaited coroutines is a common source of production bugs.
    """

    def __init__(self) -> None:
        self._handlers: defaultdict[str, list[_Subscription]] = defaultdict(list)
        self._wildcard: list[_Subscription] = []
        self._next_token = 1
        self._lock = RLock()

    def subscribe(
        self, name: str, callback: EventHandler, *, priority: int = 0, once: bool = False
    ) -> Subscription:
        if not name:
            raise ValueError("event name cannot be empty")
        if iscoroutinefunction(callback):
            raise TypeError("EventBus handlers must be synchronous; schedule async work explicitly")
        with self._lock:
            item = _Subscription(self._next_token, callback, priority, once)
            self._next_token += 1
            target = self._wildcard if name == "*" else self._handlers[name]
            target.append(item)
            target.sort(key=lambda sub: (-sub.priority, sub.token))
            return Subscription(self, name, item.token)

    def once(self, name: str, callback: EventHandler, *, priority: int = 0) -> Subscription:
        return self.subscribe(name, callback, priority=priority, once=True)

    def unsubscribe(self, name: str, token: int) -> None:
        with self._lock:
            target = self._wildcard if name == "*" else self._handlers.get(name, [])
            target[:] = [item for item in target if item.token != token]
            if name != "*" and not target:
                self._handlers.pop(name, None)

    def clear(self) -> None:
        with self._lock:
            self._handlers.clear()
            self._wildcard.clear()

    def publish(self, event: Event | str, payload: Any = None, *, source: Any = None) -> Event:
        current = event if isinstance(event, Event) else Event(event, payload, source)
        with self._lock:
            targets = list(self._handlers.get(current.name, ())) + list(self._wildcard)
        targets.sort(key=lambda sub: (-sub.priority, sub.token))
        for item in targets:
            result = item.callback(current)
            if item.once:
                self.unsubscribe(
                    current.name if item in self._handlers.get(current.name, []) else "*",
                    item.token,
                )
            if result is False or (not current.bubbles):
                break
        return current

    def emit(self, name: str, payload: Any = None, *, source: Any = None) -> Event:
        return self.publish(Event(name, payload, source))

    def listeners(self, name: str) -> Iterable[EventHandler]:
        with self._lock:
            return tuple(item.callback for item in self._handlers.get(name, ()))
