# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Shared service context and lifecycle contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from .clock import Clock
from .events import EventBus


@runtime_checkable
class System(Protocol):
    """Minimal contract for updateable game systems."""

    def update(self, delta: float) -> None: ...


@runtime_checkable
class Drawable(Protocol):
    """Minimal contract for objects that can draw through an adapter."""

    def draw(self, target: Any, *, interpolation: float = 0.0) -> None: ...


@runtime_checkable
class Lifecycle(Protocol):
    """Optional lifecycle contract used by scenes, plugins, and systems."""

    def start(self, context: GameContext) -> None: ...

    def shutdown(self) -> None: ...


@dataclass(slots=True)
class GameContext:
    """Dependency container for a game or headless simulation.

    Arbitrary services are available through `set`/`get`, while the event bus and
    clock are explicit first-class fields because almost every system uses them.
    """

    events: EventBus = field(default_factory=EventBus)
    clock: Clock = field(default_factory=Clock)
    services: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def set(self, name: str, service: Any) -> Any:
        if not name or not name.isidentifier():
            raise ValueError("service name must be a non-empty identifier")
        self.services[name] = service
        return service

    def get(self, name: str, default: Any = None) -> Any:
        return self.services.get(name, default)

    def require(self, name: str) -> Any:
        if name not in self.services:
            raise KeyError(f"required service is not registered: {name}")
        return self.services[name]

    def child(self, **metadata: Any) -> GameContext:
        child = GameContext(
            events=self.events,
            clock=self.clock,
            services=dict(self.services),
            metadata=dict(self.metadata),
        )
        child.metadata.update(metadata)
        return child


class BaseSystem:
    """Convenient base for systems that need a context but remain easy to test."""

    def __init__(self, context: GameContext | None = None) -> None:
        self.context = context or GameContext()
        self.started = False

    def start(self, context: GameContext | None = None) -> None:
        if context is not None:
            self.context = context
        self.started = True

    def update(self, delta: float) -> None:
        if not self.started:
            return

    def shutdown(self) -> None:
        self.started = False
