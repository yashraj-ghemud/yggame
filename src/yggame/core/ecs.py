# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""A small, optional entity-component-system implementation."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Any, TypeVar, cast


@dataclass(frozen=True, slots=True)
class Entity:
    """Stable handle containing an id and generation to prevent stale reuse."""

    id: int
    generation: int


C = TypeVar("C")


class World:
    """Sparse-set-like ECS world suitable for small and medium 2D games."""

    def __init__(self) -> None:
        self._next_id = 1
        self._generations: dict[int, int] = {}
        self._alive: set[int] = set()
        self._components: defaultdict[type[Any], dict[int, Any]] = defaultdict(dict)
        self._resources: dict[type[Any], Any] = {}

    def create(self, *components: Any) -> Entity:
        entity_id = self._next_id
        self._next_id += 1
        generation = self._generations.get(entity_id, 0)
        self._generations[entity_id] = generation
        self._alive.add(entity_id)
        entity = Entity(entity_id, generation)
        for component in components:
            self.add(entity, component)
        return entity

    def is_alive(self, entity: Entity) -> bool:
        return entity.id in self._alive and self._generations.get(entity.id) == entity.generation

    def destroy(self, entity: Entity) -> None:
        self._validate(entity)
        self._alive.remove(entity.id)
        for store in self._components.values():
            store.pop(entity.id, None)
        self._generations[entity.id] += 1

    def add(self, entity: Entity, component: C) -> C:
        self._validate(entity)
        self._components[type(component)][entity.id] = component
        return component

    def remove(self, entity: Entity, component_type: type[C]) -> C | None:
        self._validate(entity)
        return cast(C | None, self._components[component_type].pop(entity.id, None))

    def get(self, entity: Entity, component_type: type[C]) -> C:
        self._validate(entity)
        try:
            return cast(C, self._components[component_type][entity.id])
        except KeyError as exc:
            raise KeyError(f"entity {entity.id} lacks {component_type.__name__}") from exc

    def try_get(self, entity: Entity, component_type: type[C]) -> C | None:
        if not self.is_alive(entity):
            return None
        return cast(C | None, self._components[component_type].get(entity.id))

    def has(self, entity: Entity, *component_types: type[Any]) -> bool:
        return self.is_alive(entity) and all(
            entity.id in self._components[component_type] for component_type in component_types
        )

    def query(self, *component_types: type[Any]) -> Iterator[tuple[Entity, ...]]:
        if not component_types:
            return
        ids = set(self._components[component_types[0]])
        for component_type in component_types[1:]:
            ids.intersection_update(self._components[component_type])
        for entity_id in sorted(ids):
            if entity_id in self._alive:
                entity = Entity(entity_id, self._generations[entity_id])
                yield (entity, *(self._components[t][entity_id] for t in component_types))

    def set_resource(self, value: Any) -> Any:
        self._resources[type(value)] = value
        return value

    def get_resource(self, resource_type: type[C]) -> C | None:
        return self._resources.get(resource_type)

    def _validate(self, entity: Entity) -> None:
        if not self.is_alive(entity):
            raise KeyError(f"stale or unknown entity handle: {entity}")


@dataclass(slots=True)
class SystemEntry:
    priority: int
    callback: Callable[[World, float], None]


class SystemScheduler:
    """Runs ECS systems in stable priority order."""

    def __init__(self) -> None:
        self._systems: list[SystemEntry] = []

    def add(self, callback: Callable[[World, float], None], *, priority: int = 0) -> None:
        self._systems.append(SystemEntry(priority, callback))
        self._systems.sort(key=lambda entry: -entry.priority)

    def update(self, world: World, delta: float) -> None:
        for entry in tuple(self._systems):
            entry.callback(world, delta)
