# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Deterministic system scheduling and deferred mutation utilities."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class TaskHandle:
    id: int


@dataclass(slots=True)
class _Task:
    handle: TaskHandle
    callback: Callable[[float], bool | None]
    cancelled: bool = False


class TaskScheduler:
    """Runs small recurring tasks without exposing mutable list internals."""

    def __init__(self) -> None:
        self._tasks: dict[int, _Task] = {}
        self._next_id = 1
        self._pending_add: list[_Task] = []
        self._iterating = False

    def add(self, callback: Callable[[float], bool | None]) -> TaskHandle:
        handle = TaskHandle(self._next_id)
        self._next_id += 1
        task = _Task(handle, callback)
        if self._iterating:
            self._pending_add.append(task)
        else:
            self._tasks[handle.id] = task
        return handle

    def cancel(self, handle: TaskHandle) -> bool:
        task = self._tasks.get(handle.id)
        if task is None:
            for pending in self._pending_add:
                if pending.handle == handle:
                    pending.cancelled = True
                    return True
            return False
        task.cancelled = True
        return True

    def update(self, delta: float) -> None:
        if delta < 0:
            raise ValueError("delta cannot be negative")
        self._iterating = True
        try:
            for task in tuple(self._tasks.values()):
                if task.cancelled:
                    continue
                keep = task.callback(delta)
                if keep is False:
                    task.cancelled = True
        finally:
            self._iterating = False
            self._tasks = {
                task.handle.id: task for task in self._tasks.values() if not task.cancelled
            }
            for task in self._pending_add:
                if not task.cancelled:
                    self._tasks[task.handle.id] = task
            self._pending_add.clear()

    def clear(self) -> None:
        self._tasks.clear()
        self._pending_add.clear()

    def __len__(self) -> int:
        return len(self._tasks) + len([task for task in self._pending_add if not task.cancelled])


@dataclass(frozen=True, slots=True)
class DeferredCommand:
    callback: Callable[[], Any]
    label: str = "command"


class CommandBuffer:
    """Collects world mutations and applies them at a deterministic synchronization point."""

    def __init__(self) -> None:
        self._commands: list[DeferredCommand] = []

    def append(self, callback: Callable[[], Any], *, label: str = "command") -> None:
        self._commands.append(DeferredCommand(callback, label))

    def extend(self, commands: Iterable[DeferredCommand]) -> None:
        self._commands.extend(commands)

    def flush(self) -> list[Any]:
        results: list[Any] = []
        commands, self._commands = self._commands, []
        for command in commands:
            results.append(command.callback())
        return results

    def clear(self) -> None:
        self._commands.clear()

    def __len__(self) -> int:
        return len(self._commands)


@dataclass(frozen=True, slots=True)
class SystemSpec:
    name: str
    update: Callable[[float], None]
    before: frozenset[str] = frozenset()
    after: frozenset[str] = frozenset()
    enabled: bool = True


class SystemGraph:
    """Topologically orders systems while detecting dependency cycles clearly."""

    def __init__(self) -> None:
        self._systems: dict[str, SystemSpec] = {}
        self._ordered: tuple[SystemSpec, ...] = ()
        self._dirty = True

    def add(self, spec: SystemSpec) -> None:
        if not spec.name or spec.name in self._systems:
            raise ValueError(f"invalid or duplicate system name: {spec.name!r}")
        self._systems[spec.name] = spec
        self._dirty = True

    def remove(self, name: str) -> None:
        self._systems.pop(name)
        self._dirty = True

    def set_enabled(self, name: str, enabled: bool) -> None:
        spec = self._systems[name]
        self._systems[name] = SystemSpec(spec.name, spec.update, spec.before, spec.after, enabled)
        self._dirty = True

    def order(self) -> tuple[str, ...]:
        self._rebuild()
        return tuple(spec.name for spec in self._ordered)

    def update(self, delta: float) -> None:
        self._rebuild()
        for spec in self._ordered:
            if spec.enabled:
                spec.update(delta)

    def _rebuild(self) -> None:
        if not self._dirty:
            return
        names = set(self._systems)
        edges: dict[str, set[str]] = {name: set() for name in names}
        incoming: dict[str, int] = {name: 0 for name in names}
        for spec in self._systems.values():
            for dependency in spec.before:
                if dependency not in names:
                    raise KeyError(f"system {spec.name} depends on unknown system {dependency}")
                edges[spec.name].add(dependency)
            for dependency in spec.after:
                if dependency not in names:
                    raise KeyError(f"system {spec.name} depends on unknown system {dependency}")
                edges[dependency].add(spec.name)
        for _source, targets in edges.items():
            for target in targets:
                incoming[target] += 1
        ready = sorted(name for name, count in incoming.items() if count == 0)
        result: list[str] = []
        while ready:
            name = ready.pop(0)
            result.append(name)
            for target in sorted(edges[name]):
                incoming[target] -= 1
                if incoming[target] == 0:
                    ready.append(target)
                    ready.sort()
        if len(result) != len(names):
            raise RuntimeError("system dependency graph contains a cycle")
        self._ordered = tuple(self._systems[name] for name in result)
        self._dirty = False
