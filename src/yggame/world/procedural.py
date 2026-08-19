# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Seeded procedural generation helpers for caves, rooms, and scalar fields."""

from __future__ import annotations

import random
from dataclasses import dataclass

from yggame.core.geometry import Rect


class Noise2D:
    """Small deterministic value-noise field with smooth interpolation."""

    def __init__(self, *, seed: int = 0, cell_size: float = 32.0) -> None:
        if cell_size <= 0:
            raise ValueError("noise cell_size must be positive")
        self.seed = seed
        self.cell_size = cell_size
        self._values: dict[tuple[int, int], float] = {}

    def sample(self, x: float, y: float) -> float:
        fx, fy = x / self.cell_size, y / self.cell_size
        x0, y0 = int(fx // 1), int(fy // 1)
        tx, ty = fx - x0, fy - y0
        values = [
            self._value(ix, iy)
            for ix, iy in ((x0, y0), (x0 + 1, y0), (x0, y0 + 1), (x0 + 1, y0 + 1))
        ]
        sx, sy = self._smooth(tx), self._smooth(ty)
        top = values[0] + (values[1] - values[0]) * sx
        bottom = values[2] + (values[3] - values[2]) * sx
        return top + (bottom - top) * sy

    def fractal(
        self,
        x: float,
        y: float,
        *,
        octaves: int = 4,
        persistence: float = 0.5,
        lacunarity: float = 2.0,
    ) -> float:
        if octaves <= 0 or not 0 < persistence <= 1 or lacunarity <= 1:
            raise ValueError("invalid fractal noise parameters")
        value, amplitude, frequency, total = 0.0, 1.0, 1.0, 0.0
        for _ in range(octaves):
            value += self.sample(x * frequency, y * frequency) * amplitude
            total += amplitude
            amplitude *= persistence
            frequency *= lacunarity
        return value / total

    def _value(self, x: int, y: int) -> float:
        key = (x, y)
        if key not in self._values:
            rng = random.Random(self.seed + x * 92837111 + y * 689287499)
            self._values[key] = rng.uniform(-1.0, 1.0)
        return self._values[key]

    @staticmethod
    def _smooth(value: float) -> float:
        return value * value * (3 - 2 * value)


class CellularCaves:
    def __init__(
        self, width: int, height: int, *, seed: int = 0, fill_probability: float = 0.45
    ) -> None:
        if width <= 0 or height <= 0 or not 0 <= fill_probability <= 1:
            raise ValueError("invalid cave dimensions or fill probability")
        self.width, self.height, self.rng = width, height, random.Random(seed)
        self.fill_probability = fill_probability
        self.grid = [
            [self.rng.random() < fill_probability for _ in range(width)] for _ in range(height)
        ]

    def step(self, *, birth_limit: int = 4, death_limit: int = 3) -> None:
        updated = [[False] * self.width for _ in range(self.height)]
        for y in range(self.height):
            for x in range(self.width):
                neighbors = self._neighbors(x, y)
                if self.grid[y][x]:
                    updated[y][x] = neighbors >= death_limit
                else:
                    updated[y][x] = neighbors > birth_limit
        self.grid = updated

    def generate(self, iterations: int = 5) -> list[list[bool]]:
        if iterations < 0:
            raise ValueError("cave iterations cannot be negative")
        for _ in range(iterations):
            self.step()
        return [row[:] for row in self.grid]

    def _neighbors(self, x: int, y: int) -> int:
        total = 0
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if not dx and not dy:
                    continue
                nx, ny = x + dx, y + dy
                total += (
                    1
                    if not (0 <= nx < self.width and 0 <= ny < self.height) or self.grid[ny][nx]
                    else 0
                )
        return total


@dataclass(frozen=True, slots=True)
class Room:
    rect: Rect

    @property
    def center(self) -> tuple[int, int]:
        return int(self.rect.x + self.rect.width / 2), int(self.rect.y + self.rect.height / 2)

    def overlaps(self, other: Room, padding: int = 1) -> bool:
        return self.rect.inflated(padding * 2).intersects(other.rect)


class BSPDungeon:
    """Binary-space partitioning dungeon generator returning non-overlapping rooms."""

    def __init__(self, width: int, height: int, *, seed: int = 0, minimum_room: int = 5) -> None:
        if width <= 0 or height <= 0 or minimum_room < 3:
            raise ValueError("invalid BSP dungeon parameters")
        self.width, self.height, self.minimum_room = width, height, minimum_room
        self.rng = random.Random(seed)
        self.rooms: list[Room] = []

    def generate(self, *, splits: int = 8) -> tuple[Room, ...]:
        if splits < 0:
            raise ValueError("splits cannot be negative")
        leaves = [Rect(1, 1, self.width - 2, self.height - 2)]
        for _ in range(splits):
            index = self.rng.randrange(len(leaves))
            leaf = leaves.pop(index)
            if leaf.width >= leaf.height and leaf.width >= self.minimum_room * 2 + 2:
                first_width = self.rng.randint(
                    self.minimum_room, int(leaf.width - self.minimum_room)
                )
                leaves.extend(
                    (
                        Rect(leaf.x, leaf.y, first_width, leaf.height),
                        Rect(leaf.x + first_width, leaf.y, leaf.width - first_width, leaf.height),
                    )
                )
            elif leaf.height >= self.minimum_room * 2 + 2:
                first_height = self.rng.randint(
                    self.minimum_room, int(leaf.height - self.minimum_room)
                )
                leaves.extend(
                    (
                        Rect(leaf.x, leaf.y, leaf.width, first_height),
                        Rect(leaf.x, leaf.y + first_height, leaf.width, leaf.height - first_height),
                    )
                )
            else:
                leaves.append(leaf)
        self.rooms = []
        for leaf in leaves:
            width = self.rng.randint(self.minimum_room, max(self.minimum_room, int(leaf.width)))
            height = self.rng.randint(self.minimum_room, max(self.minimum_room, int(leaf.height)))
            x = int(leaf.x + self.rng.randint(0, max(0, int(leaf.width - width))))
            y = int(leaf.y + self.rng.randint(0, max(0, int(leaf.height - height))))
            self.rooms.append(Room(Rect(x, y, width, height)))
        return tuple(self.rooms)

    def corridors(self) -> tuple[tuple[tuple[int, int], tuple[int, int]], ...]:
        centers = [room.center for room in self.rooms]
        return tuple(zip(centers, centers[1:], strict=False))
