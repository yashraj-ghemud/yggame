# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Scene stack and transition primitives."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

from yggame.core.context import GameContext
from yggame.core.geometry import clamp


class Scene(Protocol):
    def enter(self, context: GameContext, data: SceneData) -> None: ...

    def exit(self) -> None: ...

    def update(self, delta: float) -> None: ...

    def draw(self, target: Any, interpolation: float = 0.0) -> None: ...


@dataclass(slots=True)
class SceneData:
    values: dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        return self.values.get(key, default)

    def with_values(self, **values: Any) -> SceneData:
        result = SceneData(dict(self.values))
        result.values.update(values)
        return result


class Transition:
    """Time-based transition state; rendering the visual effect is adapter-specific."""

    def __init__(self, duration: float, *, kind: str = "fade") -> None:
        if duration <= 0:
            raise ValueError("transition duration must be positive")
        self.duration = duration
        self.kind = kind
        self.elapsed = 0.0
        self.active = True

    @property
    def progress(self) -> float:
        return clamp(self.elapsed / self.duration, 0.0, 1.0)

    @property
    def finished(self) -> bool:
        return not self.active

    def update(self, delta: float) -> bool:
        self.elapsed += max(0.0, delta)
        if self.elapsed >= self.duration:
            self.elapsed = self.duration
            self.active = False
        return not self.active


@dataclass(slots=True)
class _Entry:
    name: str
    scene: Scene
    persistent: bool = False


class SceneManager:
    """Register and navigate scenes while preserving a pause-over-gameplay stack."""

    def __init__(self, context: GameContext | None = None) -> None:
        self.context = context or GameContext()
        self._factories: dict[str, Callable[[], Scene]] = {}
        self._stack: list[_Entry] = []
        self.transition: Transition | None = None

    @property
    def current(self) -> Scene | None:
        return self._stack[-1].scene if self._stack else None

    @property
    def current_name(self) -> str | None:
        return self._stack[-1].name if self._stack else None

    def register(self, name: str, factory: Callable[[], Scene]) -> None:
        if not name or name in self._factories:
            raise ValueError(f"invalid or duplicate scene name: {name!r}")
        self._factories[name] = factory

    def switch(
        self, name: str, data: SceneData | None = None, *, transition: Transition | None = None
    ) -> Scene:
        if name not in self._factories:
            raise KeyError(f"scene is not registered: {name}")
        while self._stack:
            entry = self._stack.pop()
            if not entry.persistent:
                entry.scene.exit()
        scene = self._factories[name]()
        entry = _Entry(name, scene)
        self._stack.append(entry)
        scene.enter(self.context, data or SceneData())
        self.transition = transition
        self.context.events.emit("scene_switched", {"name": name}, source=self)
        return scene

    def push(self, name: str, data: SceneData | None = None, *, persistent: bool = False) -> Scene:
        if name not in self._factories:
            raise KeyError(f"scene is not registered: {name}")
        scene = self._factories[name]()
        self._stack.append(_Entry(name, scene, persistent))
        scene.enter(self.context, data or SceneData())
        self.context.events.emit("scene_pushed", {"name": name}, source=self)
        return scene

    def pop(self) -> Scene | None:
        if not self._stack:
            return None
        entry = self._stack.pop()
        entry.scene.exit()
        self.context.events.emit("scene_popped", {"name": entry.name}, source=self)
        return entry.scene

    def update(self, delta: float) -> None:
        if self.transition:
            self.transition.update(delta)
            if self.transition.finished:
                self.transition = None
        if self.current:
            self.current.update(delta)

    def draw(self, target: Any, interpolation: float = 0.0) -> None:
        for entry in self._stack:
            entry.scene.draw(target, interpolation)

    def clear(self) -> None:
        while self._stack:
            self.pop()
