# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Deterministic tweening with common easing curves."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from yggame.core.geometry import lerp

Easing = Callable[[float], float]


def linear(value: float) -> float:
    return value


def ease_in_quad(value: float) -> float:
    return value * value


def ease_out_quad(value: float) -> float:
    return 1 - (1 - value) ** 2


def ease_in_out_quad(value: float) -> float:
    return 2 * value * value if value < 0.5 else 1 - (-2 * value + 2) ** 2 / 2


def ease_out_back(value: float) -> float:
    c1, c3 = 1.70158, 1.70158 * 1.525
    x = value - 1
    return 1 + c3 * x**3 + c1 * x**2


def ease_out_bounce(value: float) -> float:
    n1, d1 = 7.5625, 2.75
    if value < 1 / d1:
        return n1 * value * value
    if value < 2 / d1:
        value -= 1.5 / d1
        return n1 * value * value + 0.75
    if value < 2.5 / d1:
        value -= 2.25 / d1
        return n1 * value * value + 0.9375
    value -= 2.625 / d1
    return n1 * value * value + 0.984375


@dataclass(slots=True)
class Tween:
    """Tween a numeric property or value with optional repeats and yoyo mode."""

    start: float
    end: float
    duration: float
    easing: Easing = linear
    repeat: int = 0
    yoyo: bool = False
    elapsed: float = 0.0
    active: bool = True
    _cycles: int = 0

    def __post_init__(self) -> None:
        if self.duration <= 0:
            raise ValueError("tween duration must be positive")
        if self.repeat < -1:
            raise ValueError("repeat must be -1 or non-negative")

    @property
    def progress(self) -> float:
        return min(1.0, max(0.0, self.elapsed / self.duration))

    @property
    def value(self) -> float:
        amount = self.easing(self.progress)
        if self.yoyo and self._cycles % 2:
            amount = 1 - amount
        return lerp(self.start, self.end, amount)

    @property
    def finished(self) -> bool:
        return not self.active

    def update(self, delta: float) -> bool:
        if not self.active:
            return True
        self.elapsed += max(0.0, delta)
        while self.elapsed >= self.duration and self.active:
            self.elapsed -= self.duration
            self._cycles += 1
            if self.repeat != -1 and self._cycles > self.repeat:
                self.elapsed = self.duration
                self.active = False
        return not self.active


class PropertyTween:
    """Apply a tween to an object's attribute or mapping key."""

    def __init__(self, target: Any, property_name: str, tween: Tween) -> None:
        self.target, self.property_name, self.tween = target, property_name, tween

    def update(self, delta: float) -> bool:
        finished = self.tween.update(delta)
        if isinstance(self.target, dict):
            self.target[self.property_name] = self.tween.value
        else:
            setattr(self.target, self.property_name, self.tween.value)
        return finished


EASINGS: dict[str, Easing] = {
    "linear": linear,
    "ease_in_quad": ease_in_quad,
    "ease_out_quad": ease_out_quad,
    "ease_in_out_quad": ease_in_out_quad,
    "ease_out_back": ease_out_back,
    "ease_out_bounce": ease_out_bounce,
}
