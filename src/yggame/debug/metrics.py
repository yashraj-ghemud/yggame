# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Low-overhead runtime metrics and frame snapshots."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from statistics import fmean
from time import perf_counter


@dataclass(frozen=True, slots=True)
class MetricSnapshot:
    counters: dict[str, int]
    gauges: dict[str, float]
    timings_ms: dict[str, float]


class Metrics:
    def __init__(self, *, history: int = 120) -> None:
        if history <= 0:
            raise ValueError("metrics history must be positive")
        self.counters: dict[str, int] = {}
        self.gauges: dict[str, float] = {}
        self._timings: dict[str, deque[float]] = {}
        self.history = history

    def increment(self, name: str, amount: int = 1) -> int:
        self.counters[name] = self.counters.get(name, 0) + amount
        return self.counters[name]

    def set_gauge(self, name: str, value: float) -> None:
        self.gauges[name] = value

    def timing(self, name: str, elapsed_ms: float) -> None:
        self._timings.setdefault(name, deque(maxlen=self.history)).append(elapsed_ms)

    def time_block(self, name: str) -> TimingBlock:
        return TimingBlock(self, name)

    def snapshot(self) -> MetricSnapshot:
        return MetricSnapshot(
            dict(self.counters),
            dict(self.gauges),
            {name: fmean(values) for name, values in self._timings.items() if values},
        )

    def reset_frame(self) -> None:
        self.counters.clear()
        self.gauges.clear()


class TimingBlock:
    def __init__(self, metrics: Metrics, name: str) -> None:
        self.metrics, self.name, self._started = metrics, name, 0.0

    def __enter__(self) -> TimingBlock:
        self._started = perf_counter()
        return self

    def __exit__(self, *_: object) -> None:
        self.metrics.timing(self.name, (perf_counter() - self._started) * 1000.0)
