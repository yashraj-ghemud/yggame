# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Animation graph primitives for layered and parameter-driven playback."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from yggame.core.geometry import Vec2, clamp, lerp


class ParameterType(Enum):
    BOOL = "bool"
    FLOAT = "float"
    INT = "int"
    TRIGGER = "trigger"


@dataclass(slots=True)
class AnimationParameter:
    name: str
    type: ParameterType
    value: Any = False

    def set(self, value: Any) -> None:
        if self.type is ParameterType.BOOL:
            self.value = bool(value)
        elif self.type is ParameterType.FLOAT:
            self.value = float(value)
        elif self.type is ParameterType.INT:
            self.value = int(value)
        else:
            self.value = bool(value)

    def consume(self) -> bool:
        if self.type is not ParameterType.TRIGGER:
            return bool(self.value)
        value = bool(self.value)
        self.value = False
        return value


@dataclass(frozen=True, slots=True)
class GraphTransition:
    source: str
    target: str
    condition: Callable[[dict[str, AnimationParameter]], bool]
    duration: float = 0.1
    exit_time: float | None = None


@dataclass(slots=True)
class GraphState:
    name: str
    clip: Any
    speed: float = 1.0
    normalized_time: float = 0.0
    weight: float = 1.0


class AnimationGraph:
    """Finite animation graph with parameter conditions and crossfade state."""

    def __init__(self) -> None:
        self.states: dict[str, GraphState] = {}
        self.transitions: list[GraphTransition] = []
        self.parameters: dict[str, AnimationParameter] = {}
        self.current: GraphState | None = None
        self.previous: GraphState | None = None
        self.blend_elapsed = 0.0
        self.blend_duration = 0.0

    def add_parameter(
        self, name: str, type_: ParameterType, value: Any = False
    ) -> AnimationParameter:
        if name in self.parameters:
            raise ValueError(f"duplicate animation parameter: {name}")
        parameter = AnimationParameter(name, type_, value)
        self.parameters[name] = parameter
        return parameter

    def set_parameter(self, name: str, value: Any) -> None:
        self.parameters[name].set(value)

    def add_state(self, name: str, clip: Any, *, speed: float = 1.0) -> GraphState:
        if name in self.states or speed <= 0:
            raise ValueError(f"invalid or duplicate animation state: {name}")
        state = GraphState(name, clip, speed)
        self.states[name] = state
        self.current = self.current or state
        return state

    def add_transition(
        self,
        source: str,
        target: str,
        condition: Callable[[dict[str, AnimationParameter]], bool],
        *,
        duration: float = 0.1,
        exit_time: float | None = None,
    ) -> None:
        if source not in self.states or target not in self.states:
            raise KeyError("animation transition references unknown state")
        if duration < 0 or exit_time is not None and not 0 <= exit_time <= 1:
            raise ValueError("invalid animation transition timing")
        self.transitions.append(GraphTransition(source, target, condition, duration, exit_time))

    def play(self, name: str, *, immediate: bool = False) -> None:
        target = self.states[name]
        if self.current is target:
            return
        self.previous = self.current
        self.current = target
        self.current.normalized_time = 0.0
        transition = next(
            (
                item
                for item in self.transitions
                if item.source == (self.previous.name if self.previous else "")
                and item.target == name
            ),
            None,
        )
        self.blend_duration = 0.0 if immediate or transition is None else transition.duration
        self.blend_elapsed = 0.0

    def update(self, delta: float) -> None:
        if self.current is None:
            return
        for transition in self.transitions:
            if transition.source != self.current.name:
                continue
            if (
                transition.exit_time is not None
                and self.current.normalized_time < transition.exit_time
            ):
                continue
            if transition.condition(self.parameters):
                self.play(transition.target)
                break
        self.current.normalized_time = (
            self.current.normalized_time + max(0.0, delta) * self.current.speed
        ) % 1.0
        if self.previous:
            self.blend_elapsed += max(0.0, delta)
            if self.blend_elapsed >= self.blend_duration:
                self.previous = None

    @property
    def blend_weight(self) -> float:
        if self.previous is None or self.blend_duration <= 0:
            return 1.0
        return clamp(self.blend_elapsed / self.blend_duration, 0.0, 1.0)


@dataclass(frozen=True, slots=True)
class BlendSample:
    value: Any
    weight: float


class Blend1D:
    def __init__(self, parameter: str, thresholds: list[tuple[float, Any]]) -> None:
        if not thresholds:
            raise ValueError("blend tree needs at least one threshold")
        self.parameter = parameter
        self.thresholds = sorted(thresholds, key=lambda item: item[0])

    def sample(self, value: float) -> tuple[BlendSample, ...]:
        if value <= self.thresholds[0][0]:
            return (BlendSample(self.thresholds[0][1], 1.0),)
        if value >= self.thresholds[-1][0]:
            return (BlendSample(self.thresholds[-1][1], 1.0),)
        for (left_value, left), (right_value, right) in zip(
            self.thresholds, self.thresholds[1:], strict=False
        ):
            if left_value <= value <= right_value:
                amount = (value - left_value) / (right_value - left_value)
                return BlendSample(left, 1 - amount), BlendSample(right, amount)
        return (BlendSample(self.thresholds[0][1], 1.0),)


@dataclass(slots=True)
class RootMotion:
    position: Vec2 = field(default_factory=Vec2)
    rotation: float = 0.0

    def blend(self, other: RootMotion, amount: float) -> RootMotion:
        return RootMotion(
            Vec2(
                lerp(self.position.x, other.position.x, amount),
                lerp(self.position.y, other.position.y, amount),
            ),
            lerp(self.rotation, other.rotation, amount),
        )
