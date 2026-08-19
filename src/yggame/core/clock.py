# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Deterministic and real-time clock utilities."""

from __future__ import annotations

from dataclasses import dataclass
from time import monotonic

from .geometry import clamp


@dataclass(slots=True)
class Clock:
    """Game clock with separate real and simulation time.

    `tick` accepts the measured real-frame duration and returns the scaled simulation
    delta. Delta values are clamped to avoid a debugger pause producing a huge jump.
    """

    max_delta: float = 0.25
    time_scale: float = 1.0
    real_time: float = 0.0
    game_time: float = 0.0
    frame: int = 0
    paused: bool = False

    def __post_init__(self) -> None:
        if self.max_delta <= 0:
            raise ValueError("max_delta must be positive")
        self.set_time_scale(self.time_scale)

    def tick(self, real_delta: float) -> float:
        if real_delta < 0:
            raise ValueError("real_delta cannot be negative")
        bounded = min(real_delta, self.max_delta)
        self.real_time += bounded
        self.frame += 1
        simulation_delta = 0.0 if self.paused else bounded * self.time_scale
        self.game_time += simulation_delta
        return simulation_delta

    def set_time_scale(self, value: float) -> None:
        if value < 0:
            raise ValueError("time scale cannot be negative")
        self.time_scale = value

    def pause(self) -> None:
        self.paused = True

    def resume(self) -> None:
        self.paused = False


class Stopwatch:
    """A stopwatch driven by explicit deltas, making it straightforward to test."""

    __slots__ = ("elapsed", "running")

    def __init__(self) -> None:
        self.elapsed = 0.0
        self.running = False

    def start(self) -> None:
        self.running = True

    def stop(self) -> None:
        self.running = False

    def reset(self) -> None:
        self.elapsed = 0.0

    def update(self, delta: float) -> float:
        if delta < 0:
            raise ValueError("delta cannot be negative")
        if self.running:
            self.elapsed += delta
        return self.elapsed


class Timer:
    """One-shot or repeating timer that reports how many times it fired."""

    __slots__ = ("duration", "remaining", "repeat", "active")

    def __init__(self, duration: float, *, repeat: bool = False, start: bool = True) -> None:
        if duration <= 0:
            raise ValueError("duration must be positive")
        self.duration = duration
        self.remaining = duration
        self.repeat = repeat
        self.active = start

    @property
    def finished(self) -> bool:
        return not self.active and self.remaining <= 0

    def reset(self) -> None:
        self.remaining = self.duration
        self.active = True

    def cancel(self) -> None:
        self.active = False
        self.remaining = 0.0

    def update(self, delta: float) -> int:
        if delta < 0:
            raise ValueError("delta cannot be negative")
        if not self.active:
            return 0
        self.remaining -= delta
        fired = 0
        while self.remaining <= 0 and self.active:
            fired += 1
            if self.repeat:
                self.remaining += self.duration
            else:
                self.remaining = 0.0
                self.active = False
        return fired


class Cooldown(Timer):
    """Timer specialized for ability cooldown checks."""

    def __init__(self, duration: float) -> None:
        super().__init__(duration, repeat=False, start=False)

    @property
    def ready(self) -> bool:
        return not self.active

    def trigger(self) -> bool:
        if not self.ready:
            return False
        self.reset()
        return True

    @property
    def progress(self) -> float:
        return 1.0 if self.ready else clamp(1.0 - self.remaining / self.duration, 0.0, 1.0)


class RealTimeSource:
    """Monotonic wall-clock source for applications that need one."""

    def __init__(self) -> None:
        self._last = monotonic()

    def delta(self) -> float:
        now = monotonic()
        delta = max(0.0, now - self._last)
        self._last = now
        return delta
