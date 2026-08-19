# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Device-neutral action input mapping."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from yggame.core.geometry import clamp


@dataclass(slots=True)
class InputSnapshot:
    held: frozenset[str] = frozenset()
    pressed: frozenset[str] = frozenset()
    released: frozenset[str] = frozenset()
    axes: dict[str, float] = field(default_factory=dict)

    def is_down(self, action: str) -> bool:
        return action in self.held

    def was_pressed(self, action: str) -> bool:
        return action in self.pressed

    def was_released(self, action: str) -> bool:
        return action in self.released

    def axis(self, action: str, default: float = 0.0) -> float:
        return self.axes.get(action, default)


class InputMap:
    """Maps arbitrary device tokens to stable game actions."""

    def __init__(self) -> None:
        self._bindings: dict[str, set[str]] = {}
        self._held_tokens: set[str] = set()
        self._previous_actions: set[str] = set()
        self._axes: dict[str, float] = {}

    def bind(self, action: str, *tokens: str, replace: bool = False) -> None:
        if not action or not tokens:
            raise ValueError("bind requires an action and at least one token")
        target = set(tokens) if replace else self._bindings.setdefault(action, set()) | set(tokens)
        self._bindings[action] = target

    def unbind(self, action: str, *tokens: str) -> None:
        if action not in self._bindings:
            return
        if tokens:
            self._bindings[action].difference_update(tokens)
        else:
            self._bindings.pop(action)

    def set_token(self, token: str, down: bool) -> None:
        if down:
            self._held_tokens.add(token)
        else:
            self._held_tokens.discard(token)

    def set_axis(self, action: str, value: float) -> None:
        self._axes[action] = clamp(value, -1.0, 1.0)

    def update(self) -> InputSnapshot:
        actions = {
            action
            for action, tokens in self._bindings.items()
            if self._held_tokens.intersection(tokens)
        }
        snapshot = InputSnapshot(
            frozenset(actions),
            frozenset(actions - self._previous_actions),
            frozenset(self._previous_actions - actions),
            dict(self._axes),
        )
        self._previous_actions = actions
        return snapshot

    def bindings(self) -> dict[str, tuple[str, ...]]:
        return {action: tuple(sorted(tokens)) for action, tokens in self._bindings.items()}

    def load_bindings(self, values: dict[str, Iterable[str]]) -> None:
        self._bindings = {action: set(tokens) for action, tokens in values.items()}
