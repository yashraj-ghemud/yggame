# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""World regions, spawn points, and encounter scheduling utilities."""

from __future__ import annotations

import random
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Any

from yggame.core.geometry import Rect, Vec2


@dataclass(frozen=True, slots=True)
class SpawnPoint:
    id: str
    position: Vec2
    tags: frozenset[str] = frozenset()
    weight: float = 1.0
    cooldown: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id or self.weight <= 0 or self.cooldown < 0:
            raise ValueError("spawn point id, weight, or cooldown is invalid")


@dataclass(slots=True)
class Region:
    id: str
    bounds: Rect
    tags: set[str] = field(default_factory=set)
    spawn_points: dict[str, SpawnPoint] = field(default_factory=dict)
    properties: dict[str, Any] = field(default_factory=dict)

    def add_spawn(self, point: SpawnPoint) -> None:
        if point.id in self.spawn_points:
            raise ValueError(f"duplicate spawn point: {point.id}")
        if not self.bounds.contains(point.position):
            raise ValueError(f"spawn point is outside region: {point.id}")
        self.spawn_points[point.id] = point

    def contains(self, point: Vec2) -> bool:
        return self.bounds.contains(point)

    def spawns_with(self, tags: set[str] | frozenset[str]) -> tuple[SpawnPoint, ...]:
        return tuple(
            point
            for point in self.spawn_points.values()
            if not tags or tags.intersection(point.tags)
        )


class RegionMap:
    def __init__(self) -> None:
        self.regions: dict[str, Region] = {}

    def add(self, region: Region) -> None:
        if region.id in self.regions:
            raise ValueError(f"duplicate region id: {region.id}")
        self.regions[region.id] = region

    def get(self, region_id: str) -> Region:
        return self.regions[region_id]

    def at(self, position: Vec2) -> tuple[Region, ...]:
        return tuple(region for region in self.regions.values() if region.contains(position))

    def tagged(self, tag: str) -> tuple[Region, ...]:
        return tuple(region for region in self.regions.values() if tag in region.tags)

    def query(self, bounds: Rect) -> tuple[Region, ...]:
        return tuple(region for region in self.regions.values() if region.bounds.intersects(bounds))


@dataclass(slots=True)
class SpawnState:
    point: SpawnPoint
    remaining_cooldown: float = 0.0
    active_count: int = 0

    def update(self, delta: float) -> None:
        self.remaining_cooldown = max(0.0, self.remaining_cooldown - max(0.0, delta))

    @property
    def ready(self) -> bool:
        return self.remaining_cooldown <= 0 and self.active_count == 0

    def mark_spawned(self) -> None:
        self.active_count += 1
        self.remaining_cooldown = self.point.cooldown

    def mark_finished(self) -> None:
        self.active_count = max(0, self.active_count - 1)


class SpawnDirector:
    """Selects eligible points while respecting cooldowns and caller constraints."""

    def __init__(self, *, seed: int = 0) -> None:
        self.rng = random.Random(seed)
        self.states: dict[str, SpawnState] = {}
        self.max_active = 64
        self.active = 0

    def register_region(self, region: Region) -> None:
        for point in region.spawn_points.values():
            if point.id in self.states:
                raise ValueError(f"duplicate spawn point across regions: {point.id}")
            self.states[point.id] = SpawnState(point)

    def update(self, delta: float) -> None:
        for state in self.states.values():
            state.update(delta)

    def choose(
        self,
        *,
        tags: set[str] | frozenset[str] = frozenset(),
        predicate: Callable[[SpawnPoint], bool] | None = None,
    ) -> SpawnPoint | None:
        if self.active >= self.max_active:
            return None
        choices = [
            state
            for state in self.states.values()
            if state.ready
            and (not tags or tags.intersection(state.point.tags))
            and (predicate is None or predicate(state.point))
        ]
        if not choices:
            return None
        selected = self.rng.choices(
            choices, weights=[state.point.weight for state in choices], k=1
        )[0]
        selected.mark_spawned()
        self.active += 1
        return selected.point

    def finished(self, point_id: str) -> None:
        state = self.states[point_id]
        if state.active_count > 0:
            state.mark_finished()
            self.active = max(0, self.active - 1)


@dataclass(frozen=True, slots=True)
class EncounterWave:
    id: str
    entries: tuple[tuple[str, int, float], ...]
    delay: float = 0.0

    def __post_init__(self) -> None:
        if not self.id or self.delay < 0:
            raise ValueError("encounter wave id or delay is invalid")
        if any(quantity <= 0 or weight <= 0 for _, quantity, weight in self.entries):
            raise ValueError("encounter entries require positive quantity and weight")


class EncounterScheduler:
    def __init__(self, waves: Iterable[EncounterWave]) -> None:
        self.waves = tuple(waves)
        self.index = 0
        self.elapsed = 0.0
        self.active = False

    @property
    def finished(self) -> bool:
        return self.index >= len(self.waves)

    def start(self) -> None:
        self.index = 0
        self.elapsed = 0.0
        self.active = True

    def update(self, delta: float) -> EncounterWave | None:
        if not self.active or self.finished:
            return None
        self.elapsed += max(0.0, delta)
        wave = self.waves[self.index]
        if self.elapsed < wave.delay:
            return None
        self.elapsed = 0.0
        self.index += 1
        if self.finished:
            self.active = False
        return wave
