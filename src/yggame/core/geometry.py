# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Small, dependency-free 2D geometry types.

The classes intentionally use plain Python values so they can be serialized, used in
headless servers, and adapted to pygame.Rect/Vector2 at the edge of an application.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from math import cos, hypot, sin


@dataclass(slots=True)
class Vec2:
    """Mutable two-dimensional vector with predictable arithmetic semantics."""

    x: float = 0.0
    y: float = 0.0

    def copy(self) -> Vec2:
        return Vec2(self.x, self.y)

    def __add__(self, other: Vec2) -> Vec2:
        return Vec2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Vec2) -> Vec2:
        return Vec2(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> Vec2:
        return Vec2(self.x * scalar, self.y * scalar)

    __rmul__ = __mul__

    def __truediv__(self, scalar: float) -> Vec2:
        if scalar == 0:
            raise ZeroDivisionError("cannot divide a Vec2 by zero")
        return Vec2(self.x / scalar, self.y / scalar)

    def __neg__(self) -> Vec2:
        return Vec2(-self.x, -self.y)

    def __iter__(self) -> Iterator[float]:
        yield self.x
        yield self.y

    @property
    def length(self) -> float:
        return hypot(self.x, self.y)

    @property
    def length_squared(self) -> float:
        return self.x * self.x + self.y * self.y

    def normalized(self, fallback: Vec2 | None = None) -> Vec2:
        magnitude = self.length
        if magnitude <= 1e-12:
            return fallback.copy() if fallback else Vec2()
        return self / magnitude

    def dot(self, other: Vec2) -> float:
        return self.x * other.x + self.y * other.y

    def distance_to(self, other: Vec2) -> float:
        return (self - other).length

    def clamp_length(self, maximum: float) -> Vec2:
        if maximum < 0:
            raise ValueError("maximum length cannot be negative")
        magnitude = self.length
        return self if magnitude <= maximum else self.normalized() * maximum

    def rotated(self, radians: float) -> Vec2:
        c, s = cos(radians), sin(radians)
        return Vec2(self.x * c - self.y * s, self.x * s + self.y * c)

    @classmethod
    def from_polar(cls, radius: float, radians: float) -> Vec2:
        return cls(radius * cos(radians), radius * sin(radians))


@dataclass(frozen=True, slots=True)
class Rect:
    """Axis-aligned rectangle using floating-point coordinates."""

    x: float
    y: float
    width: float
    height: float

    def __post_init__(self) -> None:
        if self.width < 0 or self.height < 0:
            raise ValueError("rectangle dimensions cannot be negative")

    @property
    def left(self) -> float:
        return self.x

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def top(self) -> float:
        return self.y

    @property
    def bottom(self) -> float:
        return self.y + self.height

    @property
    def center(self) -> Vec2:
        return Vec2(self.x + self.width / 2, self.y + self.height / 2)

    def moved(self, delta: Vec2) -> Rect:
        return Rect(self.x + delta.x, self.y + delta.y, self.width, self.height)

    def inflated(self, horizontal: float, vertical: float | None = None) -> Rect:
        vertical = horizontal if vertical is None else vertical
        return Rect(
            self.x - horizontal / 2,
            self.y - vertical / 2,
            self.width + horizontal,
            self.height + vertical,
        )

    def contains(self, point: Vec2) -> bool:
        return self.left <= point.x <= self.right and self.top <= point.y <= self.bottom

    def intersects(self, other: Rect) -> bool:
        return (
            self.left < other.right
            and self.right > other.left
            and self.top < other.bottom
            and self.bottom > other.top
        )

    def intersection(self, other: Rect) -> Rect | None:
        if not self.intersects(other):
            return None
        left, top = max(self.left, other.left), max(self.top, other.top)
        right, bottom = min(self.right, other.right), min(self.bottom, other.bottom)
        return Rect(left, top, right - left, bottom - top)

    def clamp_point(self, point: Vec2) -> Vec2:
        return Vec2(
            min(max(point.x, self.left), self.right), min(max(point.y, self.top), self.bottom)
        )

    @classmethod
    def from_center(cls, center: Vec2, width: float, height: float) -> Rect:
        return cls(center.x - width / 2, center.y - height / 2, width, height)


def lerp(start: float, end: float, amount: float) -> float:
    return start + (end - start) * amount


def lerp_vec(start: Vec2, end: Vec2, amount: float) -> Vec2:
    return Vec2(lerp(start.x, end.x, amount), lerp(start.y, end.y, amount))


def clamp(value: float, minimum: float, maximum: float) -> float:
    if minimum > maximum:
        raise ValueError("minimum cannot be greater than maximum")
    return min(max(value, minimum), maximum)


def move_toward(current: float, target: float, maximum_delta: float) -> float:
    if maximum_delta < 0:
        raise ValueError("maximum_delta cannot be negative")
    if abs(target - current) <= maximum_delta:
        return target
    return current + maximum_delta if target > current else current - maximum_delta


def bounds(rectangles: Iterable[Rect]) -> Rect | None:
    items = list(rectangles)
    if not items:
        return None
    left = min(item.left for item in items)
    top = min(item.top for item in items)
    right = max(item.right for item in items)
    bottom = max(item.bottom for item in items)
    return Rect(left, top, right - left, bottom - top)
