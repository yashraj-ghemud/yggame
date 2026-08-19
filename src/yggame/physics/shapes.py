# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Shape-level collision queries and trigger processing."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from yggame.core.events import EventBus
from yggame.core.geometry import Rect, Vec2, clamp


@dataclass(frozen=True, slots=True)
class Circle:
    center: Vec2
    radius: float

    def __post_init__(self) -> None:
        if self.radius < 0:
            raise ValueError("circle radius cannot be negative")

    def bounds(self) -> Rect:
        return Rect(
            self.center.x - self.radius,
            self.center.y - self.radius,
            self.radius * 2,
            self.radius * 2,
        )


@dataclass(frozen=True, slots=True)
class AABB:
    center: Vec2
    half_size: Vec2

    def __post_init__(self) -> None:
        if self.half_size.x < 0 or self.half_size.y < 0:
            raise ValueError("AABB half-size cannot be negative")

    def bounds(self) -> Rect:
        return Rect(
            self.center.x - self.half_size.x,
            self.center.y - self.half_size.y,
            self.half_size.x * 2,
            self.half_size.y * 2,
        )


@dataclass(frozen=True, slots=True)
class CollisionManifold:
    normal: Vec2
    depth: float
    point: Vec2


def circle_circle(first: Circle, second: Circle) -> CollisionManifold | None:
    delta = second.center - first.center
    distance = delta.length
    radius = first.radius + second.radius
    if distance >= radius:
        return None
    normal = delta.normalized(Vec2(1, 0))
    return CollisionManifold(normal, radius - distance, first.center + normal * first.radius)


def aabb_aabb(first: AABB, second: AABB) -> CollisionManifold | None:
    delta = second.center - first.center
    overlap_x = first.half_size.x + second.half_size.x - abs(delta.x)
    overlap_y = first.half_size.y + second.half_size.y - abs(delta.y)
    if overlap_x <= 0 or overlap_y <= 0:
        return None
    if overlap_x < overlap_y:
        normal = Vec2(1 if delta.x >= 0 else -1, 0)
        depth = overlap_x
    else:
        normal = Vec2(0, 1 if delta.y >= 0 else -1)
        depth = overlap_y
    return CollisionManifold(normal, depth, first.center + normal * depth / 2)


def circle_aabb(circle: Circle, box: AABB) -> CollisionManifold | None:
    closest = box.bounds().clamp_point(circle.center)
    delta = circle.center - closest
    distance = delta.length
    if distance >= circle.radius:
        return None
    if distance > 1e-9:
        normal = -delta.normalized()
        return CollisionManifold(normal, circle.radius - distance, closest)
    distances = (
        (abs(circle.center.x - box.bounds().left), Vec2(-1, 0)),
        (abs(box.bounds().right - circle.center.x), Vec2(1, 0)),
        (abs(circle.center.y - box.bounds().top), Vec2(0, -1)),
        (abs(box.bounds().bottom - circle.center.y), Vec2(0, 1)),
    )
    distance_to_edge, normal = min(distances, key=lambda value: value[0])
    return CollisionManifold(
        normal, circle.radius + distance_to_edge, circle.center + normal * circle.radius
    )


def resolve_position(
    position: Vec2, manifold: CollisionManifold, *, correction: float = 0.8
) -> Vec2:
    if not 0 <= correction <= 1:
        raise ValueError("position correction must be between zero and one")
    return position - manifold.normal * manifold.depth * correction


def resolve_velocity(
    velocity: Vec2, normal: Vec2, *, restitution: float = 0.0, friction: float = 0.0
) -> Vec2:
    restitution = clamp(restitution, 0.0, 1.0)
    friction = clamp(friction, 0.0, 1.0)
    normal = normal.normalized()
    normal_speed = velocity.dot(normal)
    if normal_speed >= 0:
        return velocity
    bounced = velocity - normal * ((1 + restitution) * normal_speed)
    tangent = bounced - normal * bounced.dot(normal)
    return normal * bounced.dot(normal) + tangent * (1 - friction)


@dataclass(slots=True)
class BodyState:
    id: str
    shape: Circle | AABB
    velocity: Vec2 = field(default_factory=Vec2)
    layer: int = 1
    mask: int = -1
    sensor: bool = False
    payload: Any = None

    def overlaps(self, other: BodyState) -> CollisionManifold | None:
        if not self.layer & other.mask or not other.layer & self.mask:
            return None
        if isinstance(self.shape, Circle) and isinstance(other.shape, Circle):
            return circle_circle(self.shape, other.shape)
        if isinstance(self.shape, AABB) and isinstance(other.shape, AABB):
            return aabb_aabb(self.shape, other.shape)
        if isinstance(self.shape, Circle) and isinstance(other.shape, AABB):
            return circle_aabb(self.shape, other.shape)
        if isinstance(self.shape, AABB) and isinstance(other.shape, Circle):
            manifold = circle_aabb(other.shape, self.shape)
            return (
                CollisionManifold(-manifold.normal, manifold.depth, manifold.point)
                if manifold
                else None
            )
        return None


class TriggerZone:
    """Tracks enter/exit/stay events for sensor bodies."""

    def __init__(
        self,
        zone_id: str,
        shape: Circle | AABB,
        *,
        events: EventBus | None = None,
        layer: int = 1,
        mask: int = -1,
    ) -> None:
        self.zone_id = zone_id
        self.shape = shape
        self.events = events or EventBus()
        self.layer, self.mask = layer, mask
        self._inside: set[str] = set()

    def update(self, bodies: Iterable[BodyState]) -> None:
        current: set[str] = set()
        for body in bodies:
            if not self.layer & body.mask or not body.layer & self.mask:
                continue
            zone = BodyState(
                self.zone_id, self.shape, layer=self.layer, mask=self.mask, sensor=True
            )
            if zone.overlaps(body):
                current.add(body.id)
                if body.id not in self._inside:
                    self.events.emit(
                        "trigger_enter", {"zone": self.zone_id, "body": body}, source=self
                    )
                else:
                    self.events.emit(
                        "trigger_stay", {"zone": self.zone_id, "body": body}, source=self
                    )
        for body_id in self._inside - current:
            self.events.emit(
                "trigger_exit", {"zone": self.zone_id, "body_id": body_id}, source=self
            )
        self._inside = current

    def clear(self) -> None:
        for body_id in tuple(self._inside):
            self.events.emit(
                "trigger_exit", {"zone": self.zone_id, "body_id": body_id}, source=self
            )
        self._inside.clear()


def apply_impulse(velocity: Vec2, impulse: Vec2, *, mass: float = 1.0) -> Vec2:
    if mass <= 0:
        raise ValueError("mass must be positive")
    return velocity + impulse / mass
