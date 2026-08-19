# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Deterministic input recording and replay support."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import asdict, dataclass, field
from typing import Any

from .serialization import dumps, loads


@dataclass(frozen=True, slots=True)
class InputFrame:
    frame: int
    delta: float
    held: tuple[str, ...] = ()
    pressed: tuple[str, ...] = ()
    released: tuple[str, ...] = ()
    axes: tuple[tuple[str, float], ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Replay:
    version: int = 1
    seed: int | None = None
    frames: list[InputFrame] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __iter__(self) -> Iterator[InputFrame]:
        return iter(self.frames)

    def append(self, frame: InputFrame) -> None:
        if self.frames and frame.frame <= self.frames[-1].frame:
            raise ValueError("replay frames must have strictly increasing frame numbers")
        if frame.delta < 0:
            raise ValueError("replay frame delta cannot be negative")
        self.frames.append(frame)

    def to_json(self) -> str:
        return dumps(
            {
                "version": self.version,
                "seed": self.seed,
                "frames": [asdict(frame) for frame in self.frames],
                "metadata": self.metadata,
            },
            indent=2,
        )

    @classmethod
    def from_json(cls, text: str) -> Replay:
        raw = loads(text)
        if not isinstance(raw, dict) or not isinstance(raw.get("frames"), list):
            raise ValueError("invalid replay document")
        replay = cls(
            int(raw.get("version", 1)), raw.get("seed"), metadata=dict(raw.get("metadata", {}))
        )
        for item in raw["frames"]:
            replay.append(
                InputFrame(
                    frame=int(item["frame"]),
                    delta=float(item["delta"]),
                    held=tuple(item.get("held", ())),
                    pressed=tuple(item.get("pressed", ())),
                    released=tuple(item.get("released", ())),
                    axes=tuple(tuple(axis) for axis in item.get("axes", ())),
                    metadata=dict(item.get("metadata", {})),
                )
            )
        return replay


class ReplayRecorder:
    def __init__(self, *, seed: int | None = None) -> None:
        self.replay = Replay(seed=seed)

    def record(
        self,
        frame: int,
        delta: float,
        *,
        held: set[str] | frozenset[str] = frozenset(),
        pressed: set[str] | frozenset[str] = frozenset(),
        released: set[str] | frozenset[str] = frozenset(),
        axes: dict[str, float] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.replay.append(
            InputFrame(
                frame,
                delta,
                tuple(sorted(held)),
                tuple(sorted(pressed)),
                tuple(sorted(released)),
                tuple(sorted((axes or {}).items())),
                dict(metadata or {}),
            )
        )


class ReplayPlayer:
    def __init__(self, replay: Replay) -> None:
        self.replay = replay
        self._index = 0

    def reset(self) -> None:
        self._index = 0

    @property
    def finished(self) -> bool:
        return self._index >= len(self.replay.frames)

    def next(self) -> InputFrame:
        if self.finished:
            raise StopIteration
        frame = self.replay.frames[self._index]
        self._index += 1
        return frame

    def __iter__(self) -> Iterator[InputFrame]:
        while not self.finished:
            yield self.next()
