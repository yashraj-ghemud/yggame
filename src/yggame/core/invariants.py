# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Explicit invariant checks for development builds and deterministic tests."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class InvariantFailure:
    name: str
    message: str
    context: dict[str, Any]


class InvariantError(AssertionError):
    def __init__(self, failure: InvariantFailure) -> None:
        self.failure = failure
        super().__init__(f"{failure.name}: {failure.message}")


class Invariants:
    """Collects or raises invariant violations according to development mode."""

    def __init__(self, *, strict: bool = True) -> None:
        self.strict = strict
        self.failures: list[InvariantFailure] = []

    def check(self, name: str, condition: bool, message: str, **context: Any) -> bool:
        if condition:
            return True
        failure = InvariantFailure(name, message, dict(context))
        self.failures.append(failure)
        if self.strict:
            raise InvariantError(failure)
        return False

    def require_not_none(self, name: str, value: Any, **context: Any) -> Any:
        self.check(name, value is not None, "value must not be None", **context)
        return value

    def require_positive(self, name: str, value: float, **context: Any) -> float:
        self.check(name, value > 0, "value must be positive", value=value, **context)
        return value

    def require_unique(self, name: str, values: Iterable[Any], **context: Any) -> bool:
        materialized = list(values)
        return self.check(
            name,
            len(materialized) == len(set(materialized)),
            "values must be unique",
            values=materialized,
            **context,
        )

    def run(self, name: str, check: Callable[[], bool], message: str, **context: Any) -> bool:
        return self.check(name, check(), message, **context)

    def clear(self) -> None:
        self.failures.clear()

    @property
    def valid(self) -> bool:
        return not self.failures
