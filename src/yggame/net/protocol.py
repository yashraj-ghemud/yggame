# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Transport-neutral multiplayer primitives for authoritative and rollback games."""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

from yggame.core.serialization import dumps, loads


@dataclass(frozen=True, slots=True)
class Packet:
    kind: str
    sequence: int
    payload: dict[str, Any]
    reliable: bool = False
    acknowledged: int | None = None

    def encode(self) -> bytes:
        return dumps(
            {
                "kind": self.kind,
                "sequence": self.sequence,
                "payload": self.payload,
                "reliable": self.reliable,
                "acknowledged": self.acknowledged,
            }
        ).encode("utf-8")

    @classmethod
    def decode(cls, data: bytes) -> Packet:
        raw = loads(data.decode("utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("network packet must decode to an object")
        return cls(
            str(raw["kind"]),
            int(raw["sequence"]),
            dict(raw["payload"]),
            bool(raw.get("reliable", False)),
            raw.get("acknowledged"),
        )


class SequenceWindow:
    """Tracks recently seen sequence numbers and handles 32-bit wraparound."""

    def __init__(self, size: int = 256) -> None:
        if size <= 0:
            raise ValueError("sequence window size must be positive")
        self.size = size
        self.latest: int | None = None
        self._seen: set[int] = set()

    def accept(self, sequence: int) -> bool:
        sequence &= 0xFFFFFFFF
        if sequence in self._seen:
            return False
        if self.latest is not None and not self._newer(sequence, self.latest):
            return False
        self.latest = sequence
        self._seen.add(sequence)
        if len(self._seen) > self.size:
            oldest = sorted(
                self._seen, key=lambda item: self._distance(self.latest or 0, item), reverse=True
            )[0]
            self._seen.discard(oldest)
        return True

    @staticmethod
    def _newer(first: int, second: int) -> bool:
        return ((first - second) & 0xFFFFFFFF) < 0x80000000

    @staticmethod
    def _distance(latest: int, value: int) -> int:
        return (latest - value) & 0xFFFFFFFF


@dataclass(frozen=True, slots=True)
class InputCommand:
    tick: int
    player_id: str
    actions: tuple[str, ...] = ()
    axes: tuple[tuple[str, float], ...] = ()


class InputBuffer:
    def __init__(self, *, maximum: int = 256) -> None:
        if maximum <= 0:
            raise ValueError("input buffer maximum must be positive")
        self.maximum = maximum
        self._commands: dict[int, InputCommand] = {}

    def add(self, command: InputCommand) -> None:
        self._commands[command.tick] = command
        if len(self._commands) > self.maximum:
            oldest = min(self._commands)
            self._commands.pop(oldest)

    def get(self, tick: int) -> InputCommand | None:
        return self._commands.get(tick)

    def predict(self, tick: int, *, player_id: str) -> InputCommand:
        current = self._commands.get(tick)
        if current:
            return current
        previous_ticks = [item for item in self._commands if item < tick]
        if not previous_ticks:
            return InputCommand(tick, player_id)
        previous = self._commands[max(previous_ticks)]
        return InputCommand(tick, player_id, previous.actions, previous.axes)

    def discard_before(self, tick: int) -> None:
        for key in [key for key in self._commands if key < tick]:
            self._commands.pop(key, None)

    def __len__(self) -> int:
        return len(self._commands)


T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class Snapshot(Generic[T]):
    tick: int
    state: T
    server_time: float


class SnapshotBuffer(Generic[T]):
    """Stores snapshots and interpolates state with a caller-provided function."""

    def __init__(self, *, maximum: int = 32) -> None:
        if maximum < 2:
            raise ValueError("snapshot buffer maximum must be at least two")
        self.snapshots: deque[Snapshot[T]] = deque(maxlen=maximum)

    def add(self, snapshot: Snapshot[T]) -> None:
        if self.snapshots and snapshot.tick <= self.snapshots[-1].tick:
            return
        self.snapshots.append(snapshot)

    def sample(self, server_time: float, interpolate: Callable[[T, T, float], T]) -> T | None:
        if not self.snapshots:
            return None
        if len(self.snapshots) == 1 or server_time <= self.snapshots[0].server_time:
            return self.snapshots[0].state
        for first, second in zip(self.snapshots, list(self.snapshots)[1:], strict=False):
            if first.server_time <= server_time <= second.server_time:
                amount = (server_time - first.server_time) / max(
                    1e-9, second.server_time - first.server_time
                )
                return interpolate(first.state, second.state, amount)
        return self.snapshots[-1].state


@dataclass(slots=True)
class StateHistory(Generic[T]):
    maximum: int = 120
    states: deque[tuple[int, T]] = field(default_factory=deque)

    def __post_init__(self) -> None:
        if self.maximum <= 0:
            raise ValueError("state history maximum must be positive")
        self.states = deque(maxlen=self.maximum)

    def record(self, tick: int, state: T) -> None:
        self.states.append((tick, state))

    def get(self, tick: int) -> T | None:
        for item_tick, state in reversed(self.states):
            if item_tick == tick:
                return state
        return None

    def rollback(self, tick: int) -> T:
        for index in range(len(self.states) - 1, -1, -1):
            item_tick, state = self.states[index]
            if item_tick == tick:
                while len(self.states) > index + 1:
                    self.states.pop()
                return state
        raise KeyError(f"no state recorded for tick {tick}")
