# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Headless tilemap data model and chunk streaming primitives."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from typing import Any

from yggame.core.geometry import Rect, Vec2

GridPoint = tuple[int, int]


@dataclass(frozen=True, slots=True)
class TileDefinition:
    id: int
    name: str
    solid: bool = False
    damage: float = 0.0
    tags: frozenset[str] = frozenset()
    metadata: dict[str, Any] = field(default_factory=dict)


class TileRegistry:
    def __init__(self) -> None:
        self._tiles: dict[int, TileDefinition] = {}

    def register(self, tile: TileDefinition) -> None:
        if tile.id in self._tiles:
            raise ValueError(f"duplicate tile id: {tile.id}")
        self._tiles[tile.id] = tile

    def get(self, tile_id: int) -> TileDefinition:
        return self._tiles.get(tile_id, TileDefinition(0, "empty"))

    def all(self) -> tuple[TileDefinition, ...]:
        return tuple(sorted(self._tiles.values(), key=lambda tile: tile.id))


class TileLayer:
    def __init__(self, name: str, width: int, height: int, *, default: int = 0) -> None:
        if width <= 0 or height <= 0:
            raise ValueError("tile layer dimensions must be positive")
        self.name = name
        self.width, self.height = width, height
        self._tiles = [default] * (width * height)
        self.visible = True
        self.opacity = 1.0
        self.parallax = Vec2(1, 1)

    def _index(self, x: int, y: int) -> int:
        if not (0 <= x < self.width and 0 <= y < self.height):
            raise IndexError(f"tile coordinate outside layer: {(x, y)}")
        return y * self.width + x

    def get(self, x: int, y: int, default: int = 0) -> int:
        return (
            self._tiles[self._index(x, y)]
            if 0 <= x < self.width and 0 <= y < self.height
            else default
        )

    def set(self, x: int, y: int, tile_id: int) -> None:
        self._tiles[self._index(x, y)] = tile_id

    def fill(self, tile_id: int) -> None:
        self._tiles[:] = [tile_id] * len(self._tiles)

    def iter_tiles(self) -> Iterator[tuple[int, int, int]]:
        for y in range(self.height):
            for x in range(self.width):
                yield x, y, self._tiles[y * self.width + x]

    def copy_region(self, region: Rect) -> list[list[int]]:
        left, top = max(0, int(region.x)), max(0, int(region.y))
        right = min(self.width, int(region.right))
        bottom = min(self.height, int(region.bottom))
        return [[self.get(x, y) for x in range(left, right)] for y in range(top, bottom)]


class Tilemap:
    def __init__(self, width: int, height: int, tile_size: float = 32.0) -> None:
        if width <= 0 or height <= 0 or tile_size <= 0:
            raise ValueError("tilemap dimensions and tile_size must be positive")
        self.width, self.height, self.tile_size = width, height, tile_size
        self.registry = TileRegistry()
        self.layers: dict[str, TileLayer] = {}
        self.properties: dict[str, Any] = {}

    def add_layer(self, layer: TileLayer) -> TileLayer:
        if layer.width != self.width or layer.height != self.height:
            raise ValueError("layer dimensions must match tilemap dimensions")
        if layer.name in self.layers:
            raise ValueError(f"duplicate tilemap layer: {layer.name}")
        self.layers[layer.name] = layer
        return layer

    def layer(self, name: str) -> TileLayer:
        return self.layers[name]

    def world_to_tile(self, position: Vec2) -> GridPoint:
        return int(position.x // self.tile_size), int(position.y // self.tile_size)

    def tile_to_world(self, x: int, y: int, *, centered: bool = False) -> Vec2:
        offset = self.tile_size / 2 if centered else 0.0
        return Vec2(x * self.tile_size + offset, y * self.tile_size + offset)

    def tile_rect(self, x: int, y: int) -> Rect:
        return Rect(x * self.tile_size, y * self.tile_size, self.tile_size, self.tile_size)

    def is_solid(self, x: int, y: int, *, layer: str = "collision") -> bool:
        tile_id = self.layers[layer].get(x, y) if layer in self.layers else 0
        return self.registry.get(tile_id).solid

    def damage_at(self, x: int, y: int, *, layer: str = "collision") -> float:
        tile_id = self.layers[layer].get(x, y) if layer in self.layers else 0
        return self.registry.get(tile_id).damage

    def visible_layers(self) -> tuple[TileLayer, ...]:
        return tuple(layer for layer in self.layers.values() if layer.visible and layer.opacity > 0)


@dataclass(slots=True)
class Chunk:
    coordinate: GridPoint
    width: int
    height: int
    tiles: dict[str, list[int]] = field(default_factory=dict)
    loaded: bool = False
    dirty: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def set_layer(self, name: str, tiles: Iterable[int]) -> None:
        values = list(tiles)
        if len(values) != self.width * self.height:
            raise ValueError("chunk layer data has incorrect size")
        self.tiles[name] = values
        self.dirty = True

    def get(self, layer: str, x: int, y: int, default: int = 0) -> int:
        if not (0 <= x < self.width and 0 <= y < self.height):
            return default
        values = self.tiles.get(layer)
        return values[y * self.width + x] if values else default


class ChunkedWorld:
    """Streams chunk payloads through caller-provided load/unload callbacks."""

    def __init__(self, chunk_width: int, chunk_height: int, *, tile_size: float = 32.0) -> None:
        if chunk_width <= 0 or chunk_height <= 0:
            raise ValueError("chunk dimensions must be positive")
        self.chunk_width, self.chunk_height, self.tile_size = chunk_width, chunk_height, tile_size
        self.chunks: dict[GridPoint, Chunk] = {}
        self.loaded: set[GridPoint] = set()
        self.on_load: Any = None
        self.on_unload: Any = None

    def coordinate_for_world(self, position: Vec2) -> GridPoint:
        world_tile_x = int(position.x // self.tile_size)
        world_tile_y = int(position.y // self.tile_size)
        return world_tile_x // self.chunk_width, world_tile_y // self.chunk_height

    def ensure(self, coordinate: GridPoint) -> Chunk:
        if coordinate not in self.chunks:
            self.chunks[coordinate] = Chunk(coordinate, self.chunk_width, self.chunk_height)
        chunk = self.chunks[coordinate]
        if not chunk.loaded:
            chunk.loaded = True
            self.loaded.add(coordinate)
            if self.on_load:
                self.on_load(chunk)
        return chunk

    def unload(self, coordinate: GridPoint, *, discard: bool = False) -> None:
        chunk = self.chunks.get(coordinate)
        if chunk is None or not chunk.loaded:
            return
        if self.on_unload:
            self.on_unload(chunk)
        chunk.loaded = False
        self.loaded.discard(coordinate)
        if discard:
            self.chunks.pop(coordinate, None)

    def stream_around(
        self, center: GridPoint, radius: int
    ) -> tuple[set[GridPoint], set[GridPoint]]:
        if radius < 0:
            raise ValueError("stream radius cannot be negative")
        desired = {
            (center[0] + x, center[1] + y)
            for x in range(-radius, radius + 1)
            for y in range(-radius, radius + 1)
        }
        added = desired - self.loaded
        removed = self.loaded - desired
        for coordinate in sorted(added):
            self.ensure(coordinate)
        for coordinate in sorted(removed):
            self.unload(coordinate)
        return added, removed

    def world_tile(self, tile: GridPoint) -> tuple[GridPoint, GridPoint]:
        chunk = tile[0] // self.chunk_width, tile[1] // self.chunk_height
        local = tile[0] % self.chunk_width, tile[1] % self.chunk_height
        return chunk, local

    def get(self, layer: str, tile: GridPoint, default: int = 0) -> int:
        chunk_coord, local = self.world_tile(tile)
        return self.ensure(chunk_coord).get(layer, local[0], local[1], default)
