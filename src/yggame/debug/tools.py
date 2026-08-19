# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Runtime diagnostics that remain useful in headless builds and tests."""

from __future__ import annotations

import logging
from collections import deque
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from time import perf_counter


@dataclass(frozen=True, slots=True)
class ProfileSample:
    name: str
    elapsed_ms: float


class Profiler:
    def __init__(self, *, history: int = 120) -> None:
        if history <= 0:
            raise ValueError("profiler history must be positive")
        self.samples: dict[str, deque[float]] = {}
        self.history = history

    @contextmanager
    def measure(self, name: str) -> Iterator[None]:
        started = perf_counter()
        try:
            yield
        finally:
            samples = self.samples.setdefault(name, deque(maxlen=self.history))
            samples.append((perf_counter() - started) * 1000.0)

    def latest(self, name: str) -> ProfileSample | None:
        values = self.samples.get(name)
        return ProfileSample(name, values[-1]) if values else None

    def average_ms(self, name: str) -> float:
        values = self.samples.get(name)
        return sum(values) / len(values) if values else 0.0


class MemoryLogHandler(logging.Handler):
    """Bounded log handler suitable for an in-game console or test assertions."""

    def __init__(self, capacity: int = 500) -> None:
        super().__init__()
        self.records: deque[logging.LogRecord] = deque(maxlen=capacity)

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)

    def lines(self) -> tuple[str, ...]:
        return tuple(self.format(record) for record in self.records)


class Diagnostics:
    def __init__(self) -> None:
        self.profiler = Profiler()
        self.logger = logging.getLogger("yggame")
        self.memory_handler = MemoryLogHandler()
        self.logger.addHandler(self.memory_handler)
        self.logger.setLevel(logging.INFO)

    def close(self) -> None:
        self.logger.removeHandler(self.memory_handler)
        self.memory_handler.close()
