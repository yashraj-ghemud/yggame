# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Application host and fixed-step game loop."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from time import monotonic
from typing import Any, Protocol

from .context import GameContext
from .errors import LifecycleError


class GameSystem(Protocol):
    def update(self, delta: float) -> None: ...

    def draw(self, target: Any, interpolation: float) -> None: ...


@dataclass(slots=True)
class FrameInfo:
    frame: int
    real_delta: float
    simulation_delta: float
    interpolation: float
    updates: int


class Game:
    """Framework-neutral host for a fixed-step simulation.

    The default `run` method is intentionally headless. Applications may call
    `step` from a Pygame loop or provide callbacks for event polling and rendering.
    """

    def __init__(
        self,
        *,
        context: GameContext | None = None,
        fixed_delta: float = 1 / 60,
        max_updates_per_frame: int = 5,
        max_frame_delta: float = 0.25,
    ) -> None:
        if fixed_delta <= 0:
            raise ValueError("fixed_delta must be positive")
        if max_updates_per_frame <= 0:
            raise ValueError("max_updates_per_frame must be positive")
        self.context = context or GameContext()
        self.context.clock.max_delta = max_frame_delta
        self.fixed_delta = fixed_delta
        self.max_updates_per_frame = max_updates_per_frame
        self.systems: list[GameSystem] = []
        self.running = False
        self._accumulator = 0.0
        self._shutdown_hooks: list[Callable[[], None]] = []
        self._started = False

    def add_system(self, system: GameSystem) -> GameSystem:
        self.systems.append(system)
        if self._started and hasattr(system, "start"):
            system.start(self.context)
        return system

    def on_shutdown(self, callback: Callable[[], None]) -> None:
        self._shutdown_hooks.append(callback)

    def start(self) -> None:
        if self._started:
            raise LifecycleError("game has already started")
        self._started = True
        self.running = True
        for system in self.systems:
            if hasattr(system, "start"):
                system.start(self.context)
        self.context.events.emit("game_started", source=self)

    def stop(self) -> None:
        if not self._started:
            return
        self.running = False
        for system in reversed(self.systems):
            if hasattr(system, "shutdown"):
                system.shutdown()
        for hook in reversed(self._shutdown_hooks):
            hook()
        self.context.events.emit("game_stopped", source=self)
        self._started = False

    def pause(self) -> None:
        self.context.clock.pause()
        self.context.events.emit("game_paused", source=self)

    def resume(self) -> None:
        self.context.clock.resume()
        self.context.events.emit("game_resumed", source=self)

    def step(self, real_delta: float, *, target: Any = None, render: bool = True) -> FrameInfo:
        if not self._started:
            self.start()
        simulation_delta = self.context.clock.tick(real_delta)
        self._accumulator += simulation_delta
        updates = 0
        while self._accumulator >= self.fixed_delta and updates < self.max_updates_per_frame:
            for system in tuple(self.systems):
                system.update(self.fixed_delta)
            self._accumulator -= self.fixed_delta
            updates += 1
        if updates == self.max_updates_per_frame and self._accumulator >= self.fixed_delta:
            self._accumulator = 0.0
            self.context.events.emit("simulation_catchup_dropped", source=self)
        interpolation = self._accumulator / self.fixed_delta
        if render and target is not None:
            for system in tuple(self.systems):
                system.draw(target, interpolation)
        return FrameInfo(
            self.context.clock.frame, real_delta, simulation_delta, interpolation, updates
        )

    def run(
        self,
        *,
        frames: int | None = None,
        frame_source: Callable[[], float] | None = None,
        target: Any = None,
    ) -> None:
        source = frame_source or _monotonic_delta_source()
        count = 0
        self.start()
        try:
            while self.running and (frames is None or count < frames):
                self.step(source(), target=target)
                count += 1
        finally:
            self.stop()


def _monotonic_delta_source() -> Callable[[], float]:
    previous = monotonic()

    def source() -> float:
        nonlocal previous
        current = monotonic()
        delta = current - previous
        previous = current
        return delta

    return source
