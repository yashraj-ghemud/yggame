# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Explicit state replication contracts for multiplayer game objects."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, TypeVar

from yggame.core.serialization import CodecRegistry, dumps, loads

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class ReplicatedField:
    name: str
    reliable: bool = True
    quantize: float | None = None
    interpolate: bool = False

    def encode(self, value: Any) -> Any:
        if self.quantize and isinstance(value, (int, float)):
            return round(value / self.quantize) * self.quantize
        return value


@dataclass(frozen=True, slots=True)
class ReplicationSchema:
    component: str
    fields: tuple[ReplicatedField, ...]
    version: int = 1

    def __post_init__(self) -> None:
        names = [field.name for field in self.fields]
        if not self.component or len(names) != len(set(names)):
            raise ValueError("replication schema requires unique fields and a component name")

    def field(self, name: str) -> ReplicatedField:
        for descriptor in self.fields:
            if descriptor.name == name:
                return descriptor
        raise KeyError(f"field is not replicated: {self.component}.{name}")


@dataclass(slots=True)
class ReplicatedState:
    entity_id: str
    schema: ReplicationSchema
    values: dict[str, Any] = field(default_factory=dict)
    dirty: set[str] = field(default_factory=set)

    def set(self, name: str, value: Any) -> bool:
        descriptor = self.schema.field(name)
        encoded = descriptor.encode(value)
        changed = bool(self.values.get(name) != encoded)
        self.values[name] = encoded
        if changed:
            self.dirty.add(name)
        return changed

    def get(self, name: str, default: Any = None) -> Any:
        return self.values.get(name, default)

    def snapshot(self, *, dirty_only: bool = False) -> dict[str, Any]:
        names = self.dirty if dirty_only else {field.name for field in self.schema.fields}
        return {name: self.values[name] for name in names if name in self.values}

    def acknowledge(self) -> None:
        self.dirty.clear()


@dataclass(frozen=True, slots=True)
class StateDelta:
    tick: int
    entity_id: str
    component: str
    values: dict[str, Any]
    removed: tuple[str, ...] = ()

    def encode(self, registry: CodecRegistry | None = None) -> bytes:
        return dumps(
            {
                "tick": self.tick,
                "entity_id": self.entity_id,
                "component": self.component,
                "values": self.values,
                "removed": self.removed,
            },
            registry,
        ).encode("utf-8")

    @classmethod
    def decode(cls, data: bytes, registry: CodecRegistry | None = None) -> StateDelta:
        value = loads(data.decode("utf-8"), registry)
        if not isinstance(value, dict):
            raise ValueError("state delta must decode to an object")
        return cls(
            int(value["tick"]),
            str(value["entity_id"]),
            str(value["component"]),
            dict(value.get("values", {})),
            tuple(value.get("removed", ())),
        )


class ReplicationRegistry:
    def __init__(self) -> None:
        self.schemas: dict[str, ReplicationSchema] = {}
        self.states: dict[tuple[str, str], ReplicatedState] = {}

    def register(self, schema: ReplicationSchema) -> None:
        if schema.component in self.schemas:
            raise ValueError(f"duplicate replication schema: {schema.component}")
        self.schemas[schema.component] = schema

    def create(
        self, entity_id: str, component: str, initial: dict[str, Any] | None = None
    ) -> ReplicatedState:
        schema = self.schemas[component]
        state = ReplicatedState(entity_id, schema)
        for name, value in (initial or {}).items():
            state.set(name, value)
        self.states[(entity_id, component)] = state
        return state

    def remove(self, entity_id: str, component: str) -> None:
        self.states.pop((entity_id, component), None)

    def deltas(self, tick: int, *, dirty_only: bool = True) -> tuple[StateDelta, ...]:
        result: list[StateDelta] = []
        for state in self.states.values():
            values = state.snapshot(dirty_only=dirty_only)
            if values:
                result.append(StateDelta(tick, state.entity_id, state.schema.component, values))
                if dirty_only:
                    state.acknowledge()
        return tuple(result)

    def apply(self, delta: StateDelta) -> ReplicatedState:
        key = (delta.entity_id, delta.component)
        state = self.states.get(key) or self.create(delta.entity_id, delta.component)
        for name, value in delta.values.items():
            state.values[name] = value
        for name in delta.removed:
            state.values.pop(name, None)
        state.dirty.clear()
        return state


@dataclass(slots=True)
class Reconciliation:
    tick: int
    predicted: Any
    authoritative: Any
    correct: Callable[[Any, Any], Any]

    def apply(self) -> Any:
        return self.correct(self.predicted, self.authoritative)
