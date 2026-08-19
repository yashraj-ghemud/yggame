# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Shared contracts for the five yggame demonstration games."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from yggame.core import RandomStream, deterministic_id


@dataclass(frozen=True, slots=True)
class DemoCommand:
    name: str
    argument: str = ""

    @classmethod
    def parse(cls, value: str) -> DemoCommand:
        parts = value.strip().split(maxsplit=1)
        if not parts or not parts[0]:
            raise ValueError("demo command cannot be empty")
        return cls(parts[0].lower(), parts[1] if len(parts) > 1 else "")

    def __str__(self) -> str:
        return f"{self.name} {self.argument}".strip()


@dataclass(frozen=True, slots=True)
class DemoResult:
    game: str
    step: int
    message: str
    status: str
    score: int = 0
    changed: tuple[str, ...] = ()


@dataclass(slots=True)
class DemoTranscript:
    game: str
    seed: int
    commands: list[str] = field(default_factory=list)
    results: list[DemoResult] = field(default_factory=list)

    def record(self, command: DemoCommand, result: DemoResult) -> None:
        self.commands.append(str(command))
        self.results.append(result)

    def replay(self, game: DemoGame) -> tuple[DemoResult, ...]:
        game.reset(self.seed)
        self.results.clear()
        for raw in self.commands:
            self.results.append(game.step(DemoCommand.parse(raw)))
        return tuple(self.results)


class DemoGame(Protocol):
    name: str
    status: str
    score: int
    step_count: int

    def reset(self, seed: int) -> None: ...

    def step(self, command: DemoCommand) -> DemoResult: ...

    def summary(self) -> str: ...

    def default_commands(self) -> tuple[DemoCommand, ...]: ...

    def render_text(self) -> str: ...


def command_script(raw: str | None, default: tuple[DemoCommand, ...]) -> tuple[DemoCommand, ...]:
    if raw:
        return tuple(DemoCommand.parse(item) for item in raw.split(",") if item.strip())
    return default


def seeded_stream(seed: int, game: str) -> RandomStream:
    return RandomStream(seed, name=f"demo:{game}")


def id_for(seed: int, *parts: Any) -> str:
    return deterministic_id(seed, *parts)


def status_score_message(game: DemoGame, message: str, changed: tuple[str, ...] = ()) -> DemoResult:
    return DemoResult(game.name, game.step_count, message, game.status, game.score, changed)
