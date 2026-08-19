# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Reproducible random streams for gameplay, procedural generation, and replays."""

from __future__ import annotations

import hashlib
import random
from collections.abc import Sequence
from typing import Any, TypeVar, cast

T = TypeVar("T")


class RandomStream:
    """Named deterministic RNG stream that avoids coupling systems to global random state."""

    def __init__(self, seed: int | str = 0, *, name: str = "default") -> None:
        self.name = name
        self.seed = derive_seed(seed, name)
        self._rng = random.Random(self.seed)

    def fork(self, name: str) -> RandomStream:
        return RandomStream(self.seed, name=f"{self.name}:{name}")

    def random(self) -> float:
        return self._rng.random()

    def uniform(self, minimum: float, maximum: float) -> float:
        return self._rng.uniform(minimum, maximum)

    def integer(self, minimum: int, maximum: int) -> int:
        return self._rng.randint(minimum, maximum)

    def choice(self, values: Sequence[T]) -> T:
        if not values:
            raise IndexError("cannot choose from an empty sequence")
        return values[self._rng.randrange(len(values))]

    def choices(
        self, values: Sequence[T], weights: Sequence[float] | None = None, *, count: int = 1
    ) -> list[T]:
        if not values or count < 0:
            raise ValueError("random choices require values and non-negative count")
        if weights is not None and len(weights) != len(values):
            raise ValueError("weights must have the same length as values")
        return self._rng.choices(values, weights=weights, k=count)

    def shuffle(self, values: list[T]) -> None:
        self._rng.shuffle(values)

    def sample(self, values: Sequence[T], count: int) -> list[T]:
        return self._rng.sample(values, count)

    def chance(self, probability: float) -> bool:
        if not 0 <= probability <= 1:
            raise ValueError("probability must be between zero and one")
        return self.random() < probability

    def state(self) -> object:
        return self._rng.getstate()

    def restore(self, state: object) -> None:
        self._rng.setstate(cast(tuple[Any, ...], state))


def derive_seed(seed: int | str, namespace: str = "") -> int:
    """Derive a stable 64-bit seed without relying on Python's process-randomized hash."""
    payload = f"{seed}:{namespace}".encode()
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big", signed=False)


def weighted_choice(stream: RandomStream, values: Sequence[T], weights: Sequence[float]) -> T:
    return stream.choices(values, weights, count=1)[0]


def deterministic_id(seed: int | str, *parts: Any, length: int = 12) -> str:
    if length <= 0:
        raise ValueError("deterministic id length must be positive")
    payload = ":".join(str(part) for part in (seed, *parts)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:length]
