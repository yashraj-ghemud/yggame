# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Composable AI decision primitives."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any


class Status(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    RUNNING = "running"


class StateMachine:
    def __init__(self) -> None:
        self.states: dict[str, Callable[[float, dict[str, Any]], str | None]] = {}
        self.current: str | None = None
        self.state_time = 0.0
        self.blackboard: dict[str, Any] = {}

    def add(self, name: str, update: Callable[[float, dict[str, Any]], str | None]) -> None:
        if name in self.states:
            raise ValueError(f"duplicate AI state: {name}")
        self.states[name] = update
        self.current = self.current or name

    def transition(self, name: str) -> None:
        if name not in self.states:
            raise KeyError(f"unknown AI state: {name}")
        self.current = name
        self.state_time = 0.0

    def update(self, delta: float) -> None:
        if self.current is None:
            return
        next_state = self.states[self.current](delta, self.blackboard)
        self.state_time += max(0.0, delta)
        if next_state is not None and next_state != self.current:
            self.transition(next_state)


class Node:
    def tick(self, delta: float, blackboard: dict[str, Any]) -> Status:
        raise NotImplementedError


@dataclass(slots=True)
class Action(Node):
    callback: Callable[[float, dict[str, Any]], Status]

    def tick(self, delta: float, blackboard: dict[str, Any]) -> Status:
        return self.callback(delta, blackboard)


@dataclass(slots=True)
class Condition(Node):
    predicate: Callable[[dict[str, Any]], bool]

    def tick(self, delta: float, blackboard: dict[str, Any]) -> Status:
        return Status.SUCCESS if self.predicate(blackboard) else Status.FAILURE


class Sequence(Node):
    def __init__(self, *children: Node) -> None:
        self.children = list(children)
        self.index = 0

    def tick(self, delta: float, blackboard: dict[str, Any]) -> Status:
        while self.index < len(self.children):
            result = self.children[self.index].tick(delta, blackboard)
            if result is Status.RUNNING:
                return result
            if result is Status.FAILURE:
                self.index = 0
                return result
            self.index += 1
        self.index = 0
        return Status.SUCCESS


class Selector(Node):
    def __init__(self, *children: Node) -> None:
        self.children = list(children)
        self.index = 0

    def tick(self, delta: float, blackboard: dict[str, Any]) -> Status:
        while self.index < len(self.children):
            result = self.children[self.index].tick(delta, blackboard)
            if result is Status.RUNNING:
                return result
            if result is Status.SUCCESS:
                self.index = 0
                return result
            self.index += 1
        self.index = 0
        return Status.FAILURE


class Inverter(Node):
    def __init__(self, child: Node) -> None:
        self.child = child

    def tick(self, delta: float, blackboard: dict[str, Any]) -> Status:
        result = self.child.tick(delta, blackboard)
        return {Status.SUCCESS: Status.FAILURE, Status.FAILURE: Status.SUCCESS}.get(result, result)


class BehaviorTree:
    def __init__(self, root: Node, *, blackboard: dict[str, Any] | None = None) -> None:
        self.root = root
        self.blackboard = blackboard if blackboard is not None else {}

    def tick(self, delta: float) -> Status:
        return self.root.tick(delta, self.blackboard)
