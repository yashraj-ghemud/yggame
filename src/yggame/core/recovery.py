# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Runtime recovery and checkpoint policies for long-running game sessions."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from time import monotonic
from typing import Any


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    attempts: int = 3
    initial_delay: float = 0.25
    multiplier: float = 2.0
    maximum_delay: float = 10.0

    def __post_init__(self) -> None:
        if (
            self.attempts < 1
            or self.initial_delay < 0
            or self.multiplier < 1
            or self.maximum_delay < 0
        ):
            raise ValueError("invalid retry policy")

    def delay(self, attempt: int) -> float:
        if attempt < 0:
            raise ValueError("attempt cannot be negative")
        return min(self.maximum_delay, self.initial_delay * self.multiplier**attempt)


@dataclass(frozen=True, slots=True)
class Checkpoint:
    name: str
    created_at: float
    state: Any
    generation: int


class RecoveryManager:
    """Keeps bounded in-memory checkpoints and restores the newest valid state."""

    def __init__(self, *, maximum: int = 8, clock: Callable[[], float] | None = None) -> None:
        if maximum <= 0:
            raise ValueError("checkpoint maximum must be positive")
        self.maximum = maximum
        self.clock = clock or monotonic
        self._checkpoints: list[Checkpoint] = []
        self._generation = 0

    def checkpoint(self, name: str, state: Any) -> Checkpoint:
        if not name:
            raise ValueError("checkpoint name cannot be empty")
        self._generation += 1
        checkpoint = Checkpoint(name, self.clock(), state, self._generation)
        self._checkpoints.append(checkpoint)
        self._checkpoints = self._checkpoints[-self.maximum :]
        return checkpoint

    def latest(self, name: str | None = None) -> Checkpoint | None:
        values = (
            self._checkpoints
            if name is None
            else [item for item in self._checkpoints if item.name == name]
        )
        return values[-1] if values else None

    def restore(self, name: str | None = None) -> Any:
        checkpoint = self.latest(name)
        if checkpoint is None:
            raise LookupError("no checkpoint is available")
        return checkpoint.state

    def discard(self, name: str | None = None) -> None:
        if name is None:
            self._checkpoints.clear()
        else:
            self._checkpoints[:] = [item for item in self._checkpoints if item.name != name]

    def names(self) -> tuple[str, ...]:
        return tuple(item.name for item in self._checkpoints)


class RetryExecutor:
    def __init__(
        self, policy: RetryPolicy | None = None, *, sleeper: Callable[[float], None] | None = None
    ) -> None:
        self.policy = policy or RetryPolicy()
        self.sleeper = sleeper or (lambda _delay: None)

    def run(self, operation: Callable[[int], Any]) -> Any:
        last_error: Exception | None = None
        for attempt in range(self.policy.attempts):
            try:
                return operation(attempt)
            except Exception as exc:
                last_error = exc
                if attempt + 1 < self.policy.attempts:
                    self.sleeper(self.policy.delay(attempt))
        raise RuntimeError("operation failed after retry policy was exhausted") from last_error
