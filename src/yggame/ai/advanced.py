# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Advanced AI utilities for responsive 2D NPCs."""

from __future__ import annotations

import math
import random
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Any

from yggame.core.clock import Cooldown
from yggame.core.geometry import Rect, Vec2, clamp

from .behavior import Node, Status


class Repeat(Node):
    def __init__(self, child: Node, count: int = -1) -> None:
        if count == 0 or count < -1:
            raise ValueError("repeat count must be positive or -1")
        self.child, self.count, self.completed = child, count, 0

    def tick(self, delta: float, blackboard: dict[str, Any]) -> Status:
        result = self.child.tick(delta, blackboard)
        if result is Status.RUNNING:
            return result
        if result is Status.FAILURE:
            self.completed = 0
            return result
        self.completed += 1
        if self.count != -1 and self.completed >= self.count:
            self.completed = 0
            return Status.SUCCESS
        return Status.RUNNING


class CooldownNode(Node):
    def __init__(self, child: Node, duration: float) -> None:
        self.child = child
        self.cooldown = Cooldown(duration)

    def tick(self, delta: float, blackboard: dict[str, Any]) -> Status:
        self.cooldown.update(delta)
        if not self.cooldown.ready:
            return Status.FAILURE
        result = self.child.tick(delta, blackboard)
        if result is Status.SUCCESS:
            self.cooldown.trigger()
        return result


class Timeout(Node):
    def __init__(self, child: Node, duration: float) -> None:
        if duration <= 0:
            raise ValueError("timeout duration must be positive")
        self.child, self.duration, self.elapsed = child, duration, 0.0

    def tick(self, delta: float, blackboard: dict[str, Any]) -> Status:
        self.elapsed += max(0.0, delta)
        if self.elapsed >= self.duration:
            self.elapsed = 0.0
            return Status.FAILURE
        result = self.child.tick(delta, blackboard)
        if result is not Status.RUNNING:
            self.elapsed = 0.0
        return result


class Succeeder(Node):
    def __init__(self, child: Node) -> None:
        self.child = child

    def tick(self, delta: float, blackboard: dict[str, Any]) -> Status:
        self.child.tick(delta, blackboard)
        return Status.SUCCESS


@dataclass(frozen=True, slots=True)
class UtilityAction:
    name: str
    score: Callable[[dict[str, Any]], float]
    execute: Callable[[float, dict[str, Any]], Status]


class UtilitySelector(Node):
    def __init__(self, actions: Iterable[UtilityAction], *, randomize_ties: bool = False) -> None:
        self.actions = tuple(actions)
        if not self.actions:
            raise ValueError("utility selector requires actions")
        self.randomize_ties = randomize_ties
        self.rng = random.Random(0)
        self.current: UtilityAction | None = None

    def tick(self, delta: float, blackboard: dict[str, Any]) -> Status:
        best_score = max(action.score(blackboard) for action in self.actions)
        candidates = [action for action in self.actions if action.score(blackboard) == best_score]
        self.current = self.rng.choice(candidates) if self.randomize_ties else candidates[0]
        result = self.current.execute(delta, blackboard)
        if result is not Status.RUNNING:
            self.current = None
        return result


@dataclass(slots=True)
class SteeringAgent:
    position: Vec2
    velocity: Vec2 = field(default_factory=Vec2)
    maximum_speed: float = 150.0
    maximum_force: float = 400.0
    mass: float = 1.0

    def apply(self, desired_velocity: Vec2, delta: float) -> Vec2:
        desired = desired_velocity.clamp_length(self.maximum_speed)
        steering = (desired - self.velocity).clamp_length(self.maximum_force)
        self.velocity = (self.velocity + steering * (delta / self.mass)).clamp_length(
            self.maximum_speed
        )
        self.position = self.position + self.velocity * delta
        return self.velocity

    def seek(self, target: Vec2, delta: float, *, slowing_radius: float = 0.0) -> Vec2:
        offset = target - self.position
        distance = offset.length
        speed = self.maximum_speed
        if slowing_radius > 0:
            speed *= clamp(distance / slowing_radius, 0.0, 1.0)
        return self.apply(offset.normalized() * speed, delta)

    def flee(self, target: Vec2, delta: float, *, slowing_radius: float = 0.0) -> Vec2:
        return self.seek(
            self.position + (self.position - target), delta, slowing_radius=slowing_radius
        )

    def arrive(self, target: Vec2, delta: float, slowing_radius: float) -> Vec2:
        return self.seek(target, delta, slowing_radius=slowing_radius)

    def wander(
        self, delta: float, *, angle: float = 0.0, radius: float = 40.0, distance: float = 50.0
    ) -> Vec2:
        target = self.position + self.velocity.normalized(Vec2(1, 0)) * distance
        return self.seek(target + Vec2.from_polar(radius, angle), delta)


def separate(
    agent: SteeringAgent, neighbors: Iterable[SteeringAgent], radius: float, delta: float
) -> Vec2:
    force = Vec2()
    for neighbor in neighbors:
        offset = agent.position - neighbor.position
        distance = offset.length
        if 1e-6 < distance < radius:
            force += offset.normalized() * (radius - distance) / radius
    return agent.apply(force * agent.maximum_speed, delta)


@dataclass(frozen=True, slots=True)
class VisionCone:
    position: Vec2
    forward: Vec2
    distance: float
    angle_degrees: float

    def sees(self, target: Vec2, *, obstacles: Iterable[Rect] = ()) -> bool:
        offset = target - self.position
        if offset.length > self.distance:
            return False
        direction = offset.normalized()
        dot = clamp(self.forward.normalized(Vec2(1, 0)).dot(direction), -1, 1)
        if math.degrees(math.acos(dot)) > self.angle_degrees / 2:
            return False
        for obstacle in obstacles:
            if _segment_intersects_rect(self.position, target, obstacle):
                return False
        return True


@dataclass(frozen=True, slots=True)
class HearingEvent:
    position: Vec2
    loudness: float
    source: Any = None


class Perception:
    def __init__(self, vision: VisionCone, *, hearing_radius: float = 200.0) -> None:
        if hearing_radius < 0:
            raise ValueError("hearing radius cannot be negative")
        self.vision = vision
        self.hearing_radius = hearing_radius
        self.last_seen: Vec2 | None = None
        self.last_heard: HearingEvent | None = None

    def observe(self, target: Vec2, *, obstacles: Iterable[Rect] = ()) -> bool:
        visible = self.vision.sees(target, obstacles=obstacles)
        if visible:
            self.last_seen = target.copy()
        return visible

    def hear(self, event: HearingEvent) -> bool:
        heard = self.vision.position.distance_to(event.position) <= self.hearing_radius * max(
            0, event.loudness
        )
        if heard:
            self.last_heard = event
        return heard


def _segment_intersects_rect(start: Vec2, end: Vec2, rect: Rect) -> bool:
    direction = end - start
    t_min, t_max = 0.0, 1.0
    for origin, delta, low, high in (
        (start.x, direction.x, rect.left, rect.right),
        (start.y, direction.y, rect.top, rect.bottom),
    ):
        if abs(delta) < 1e-9:
            if origin < low or origin > high:
                return False
            continue
        near, far = (low - origin) / delta, (high - origin) / delta
        if near > far:
            near, far = far, near
        t_min, t_max = max(t_min, near), min(t_max, far)
        if t_min > t_max:
            return False
    return True
