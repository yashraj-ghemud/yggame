# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Opt-in, privacy-conscious telemetry primitives for local diagnostics."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from time import monotonic
from typing import Any


@dataclass(frozen=True, slots=True)
class TelemetryEvent:
    name: str
    timestamp: float
    properties: dict[str, Any] = field(default_factory=dict)


class Telemetry:
    """In-memory telemetry sink with bounded retention and explicit export."""

    def __init__(self, *, capacity: int = 1000, enabled: bool = True) -> None:
        if capacity <= 0:
            raise ValueError("telemetry capacity must be positive")
        self.capacity = capacity
        self.enabled = enabled
        self.events: deque[TelemetryEvent] = deque(maxlen=capacity)
        self.counters: dict[str, int] = {}

    def record(self, name: str, **properties: Any) -> TelemetryEvent | None:
        if not self.enabled:
            return None
        if not name:
            raise ValueError("telemetry event name cannot be empty")
        event = TelemetryEvent(name, monotonic(), dict(properties))
        self.events.append(event)
        self.counters[name] = self.counters.get(name, 0) + 1
        return event

    def increment(self, name: str, amount: int = 1, **properties: Any) -> int:
        self.record(name, amount=amount, **properties)
        self.counters[name] = self.counters.get(name, 0) + amount - 1
        return self.counters[name]

    def clear(self) -> None:
        self.events.clear()
        self.counters.clear()

    def export(self) -> dict[str, Any]:
        return {
            "counters": dict(self.counters),
            "events": [
                {
                    "name": event.name,
                    "timestamp": event.timestamp,
                    "properties": dict(event.properties),
                }
                for event in self.events
            ],
        }


class Breadcrumbs:
    """Bounded chronological context trail for crash reports."""

    def __init__(self, capacity: int = 64) -> None:
        if capacity <= 0:
            raise ValueError("breadcrumb capacity must be positive")
        self.items: deque[str] = deque(maxlen=capacity)

    def add(self, message: str) -> None:
        if message:
            self.items.append(message)

    def extend(self, messages: list[str] | tuple[str, ...]) -> None:
        for message in messages:
            self.add(message)

    def snapshot(self) -> tuple[str, ...]:
        return tuple(self.items)

    def clear(self) -> None:
        self.items.clear()
