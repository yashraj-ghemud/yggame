# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Deterministic 2D particle and lightweight VFX primitives."""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from math import radians
from typing import Any

from yggame.core.geometry import Vec2, clamp, lerp


class EmitterShape(Enum):
    POINT = "point"
    CIRCLE = "circle"
    LINE = "line"
    CONE = "cone"
    RECTANGLE = "rectangle"


@dataclass(frozen=True, slots=True)
class Range:
    minimum: float
    maximum: float

    def __post_init__(self) -> None:
        if self.minimum > self.maximum:
            raise ValueError("range minimum cannot exceed maximum")

    def sample(self, rng: random.Random) -> float:
        return rng.uniform(self.minimum, self.maximum)


@dataclass(frozen=True, slots=True)
class ParticleConfig:
    lifetime: Range = Range(0.4, 0.8)
    speed: Range = Range(20.0, 80.0)
    angle_degrees: Range = Range(0.0, 360.0)
    gravity: Vec2 = field(default_factory=lambda: Vec2(0.0, 80.0))
    start_scale: Range = Range(0.7, 1.0)
    end_scale: Range = Range(0.0, 0.2)
    start_alpha: Range = Range(1.0, 1.0)
    end_alpha: Range = Range(0.0, 0.0)
    emission_rate: float = 20.0
    burst: int = 0
    maximum: int = 500

    def __post_init__(self) -> None:
        if self.emission_rate < 0 or self.burst < 0 or self.maximum <= 0:
            raise ValueError("particle emission and maximum values are invalid")


@dataclass(slots=True)
class Particle:
    position: Vec2
    velocity: Vec2
    lifetime: float
    age: float
    start_scale: float
    end_scale: float
    start_alpha: float
    end_alpha: float
    rotation: float = 0.0
    angular_velocity: float = 0.0
    color: Any = None

    @property
    def alive(self) -> bool:
        return self.age < self.lifetime

    @property
    def normalized_age(self) -> float:
        return clamp(self.age / self.lifetime, 0.0, 1.0)

    @property
    def scale(self) -> float:
        return lerp(self.start_scale, self.end_scale, self.normalized_age)

    @property
    def alpha(self) -> float:
        return lerp(self.start_alpha, self.end_alpha, self.normalized_age)

    def update(self, delta: float, gravity: Vec2) -> None:
        self.age += max(0.0, delta)
        self.velocity = self.velocity + gravity * max(0.0, delta)
        self.position = self.position + self.velocity * max(0.0, delta)
        self.rotation += self.angular_velocity * max(0.0, delta)


class ParticleSystem:
    """Emitter with seeded randomness, burst support, and bounded particle count."""

    def __init__(self, config: ParticleConfig | None = None, *, seed: int | None = None) -> None:
        self.config = config or ParticleConfig()
        self.rng = random.Random(seed)
        self.position = Vec2()
        self.shape = EmitterShape.POINT
        self.shape_size = Vec2(0, 0)
        self.cone_angle = 30.0
        self.particles: list[Particle] = []
        self.emitting = False
        self._emission_remainder = 0.0
        self._burst_pending = 0
        self.on_spawn: Callable[[Particle], None] | None = None
        self.on_expire: Callable[[Particle], None] | None = None

    def start(self, *, burst: bool = True) -> None:
        self.emitting = True
        if burst:
            self._burst_pending += self.config.burst

    def stop(self, *, clear: bool = False) -> None:
        self.emitting = False
        if clear:
            self.clear()

    def burst(self, count: int | None = None) -> None:
        self._burst_pending += self.config.burst if count is None else max(0, count)

    def clear(self) -> None:
        self.particles.clear()
        self._emission_remainder = 0.0
        self._burst_pending = 0

    def update(self, delta: float) -> None:
        delta = max(0.0, delta)
        if self.emitting:
            self._emission_remainder += delta * self.config.emission_rate
            count = int(self._emission_remainder)
            self._emission_remainder -= count
            count += self._burst_pending
            self._burst_pending = 0
            for _ in range(count):
                if len(self.particles) >= self.config.maximum:
                    break
                self.spawn()
        alive: list[Particle] = []
        for particle in self.particles:
            particle.update(delta, self.config.gravity)
            if particle.alive:
                alive.append(particle)
            elif self.on_expire:
                self.on_expire(particle)
        self.particles = alive

    def spawn(self) -> Particle:
        angle = self.config.angle_degrees.sample(self.rng)
        if self.shape is EmitterShape.CONE:
            angle = self.rng.uniform(-self.cone_angle / 2, self.cone_angle / 2) + angle
        position = self._sample_position()
        speed = self.config.speed.sample(self.rng)
        velocity = Vec2.from_polar(speed, radians(angle))
        particle = Particle(
            position,
            velocity,
            self.config.lifetime.sample(self.rng),
            0.0,
            self.config.start_scale.sample(self.rng),
            self.config.end_scale.sample(self.rng),
            self.config.start_alpha.sample(self.rng),
            self.config.end_alpha.sample(self.rng),
            angular_velocity=self.rng.uniform(-180.0, 180.0),
        )
        self.particles.append(particle)
        if self.on_spawn:
            self.on_spawn(particle)
        return particle

    def _sample_position(self) -> Vec2:
        if self.shape is EmitterShape.POINT:
            return self.position.copy()
        if self.shape is EmitterShape.CIRCLE:
            angle = self.rng.uniform(0, 6.283185307)
            radius = self.rng.uniform(0, max(self.shape_size.x, self.shape_size.y))
            return self.position + Vec2.from_polar(radius, angle)
        if self.shape is EmitterShape.LINE:
            return self.position + Vec2(
                self.rng.uniform(-self.shape_size.x / 2, self.shape_size.x / 2), 0
            )
        if self.shape is EmitterShape.RECTANGLE:
            return self.position + Vec2(
                self.rng.uniform(-self.shape_size.x / 2, self.shape_size.x / 2),
                self.rng.uniform(-self.shape_size.y / 2, self.shape_size.y / 2),
            )
        return self.position.copy()


@dataclass(slots=True)
class TrailPoint:
    position: Vec2
    age: float = 0.0


class TrailEffect:
    def __init__(self, *, lifetime: float = 0.25, maximum_points: int = 32) -> None:
        if lifetime <= 0 or maximum_points <= 1:
            raise ValueError("trail lifetime must be positive and maximum_points greater than one")
        self.lifetime = lifetime
        self.maximum_points = maximum_points
        self.points: list[TrailPoint] = []

    def add(self, position: Vec2) -> None:
        if self.points and self.points[-1].position.distance_to(position) < 0.5:
            return
        self.points.append(TrailPoint(position.copy()))
        del self.points[: -self.maximum_points]

    def update(self, delta: float) -> None:
        for point in self.points:
            point.age += max(0.0, delta)
        self.points[:] = [point for point in self.points if point.age < self.lifetime]

    def alpha(self, point: TrailPoint) -> float:
        return 1.0 - clamp(point.age / self.lifetime, 0.0, 1.0)


@dataclass(frozen=True, slots=True)
class HitSpark:
    position: Vec2
    direction: Vec2 = field(default_factory=lambda: Vec2(0, -1))
    intensity: float = 1.0
    color: Any = None
    lifetime: float = 0.12

    def create_particles(self, *, seed: int | None = None) -> ParticleSystem:
        strength = max(0.1, self.intensity)
        config = ParticleConfig(
            lifetime=Range(self.lifetime * 0.5, self.lifetime),
            speed=Range(80 * strength, 220 * strength),
            angle_degrees=Range(-60, 60),
            gravity=Vec2(0, 160),
            start_scale=Range(0.8, 1.3),
            end_scale=Range(0.0, 0.1),
            emission_rate=0,
            burst=max(3, int(8 * strength)),
            maximum=64,
        )
        system = ParticleSystem(config, seed=seed)
        system.position = self.position.copy()
        system.start()
        return system
