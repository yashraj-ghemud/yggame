# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Device-neutral input helpers for keyboards, gamepads, touch, and combos."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from yggame.core.geometry import Vec2, clamp


@dataclass(slots=True)
class DeviceState:
    name: str
    connected: bool = True
    buttons: set[str] = field(default_factory=set)
    axes: dict[str, float] = field(default_factory=dict)

    def set_button(self, button: str, pressed: bool) -> None:
        if pressed:
            self.buttons.add(button)
        else:
            self.buttons.discard(button)

    def set_axis(self, axis: str, value: float, *, deadzone: float = 0.08) -> None:
        value = clamp(value, -1.0, 1.0)
        self.axes[axis] = 0.0 if abs(value) < deadzone else value


class GamepadManager:
    def __init__(self) -> None:
        self.devices: dict[str, DeviceState] = {}
        self.rumble_requests: list[tuple[str, float, float, float]] = []

    def connect(self, device_id: str) -> DeviceState:
        if not device_id:
            raise ValueError("gamepad device id cannot be empty")
        state = self.devices.setdefault(device_id, DeviceState(device_id))
        state.connected = True
        return state

    def disconnect(self, device_id: str) -> None:
        if device_id in self.devices:
            self.devices[device_id].connected = False

    def get(self, device_id: str) -> DeviceState:
        return self.devices[device_id]

    def rumble(self, device_id: str, low: float, high: float, duration: float) -> None:
        if not 0 <= low <= 1 or not 0 <= high <= 1 or duration < 0:
            raise ValueError("rumble values are outside valid ranges")
        self.rumble_requests.append((device_id, low, high, duration))


@dataclass(frozen=True, slots=True)
class Chord:
    actions: frozenset[str]
    output: str

    def matches(self, held: set[str] | frozenset[str]) -> bool:
        return self.actions.issubset(held)


class ComboDetector:
    def __init__(self, *, maximum_history: int = 32) -> None:
        if maximum_history <= 0:
            raise ValueError("combo history must be positive")
        self.maximum_history = maximum_history
        self.history: list[tuple[str, float]] = []
        self.combos: list[tuple[tuple[str, ...], str, float]] = []

    def register(self, sequence: Iterable[str], output: str, *, timeout: float = 0.8) -> None:
        values = tuple(sequence)
        if not values or timeout <= 0:
            raise ValueError("combo sequences require actions and a positive timeout")
        self.combos.append((values, output, timeout))

    def push(self, action: str, timestamp: float) -> str | None:
        self.history.append((action, timestamp))
        self.history = self.history[-self.maximum_history :]
        for sequence, output, timeout in sorted(
            self.combos, key=lambda item: len(item[0]), reverse=True
        ):
            if len(self.history) < len(sequence):
                continue
            recent = self.history[-len(sequence) :]
            if tuple(item[0] for item in recent) != sequence:
                continue
            if recent[-1][1] - recent[0][1] <= timeout:
                return output
        return None


@dataclass(slots=True)
class VirtualControl:
    id: str
    rect: tuple[float, float, float, float]
    pressed: bool = False
    value: Vec2 = field(default_factory=Vec2)

    def contains(self, point: Vec2) -> bool:
        x, y, width, height = self.rect
        return x <= point.x <= x + width and y <= point.y <= y + height


class TouchInput:
    def __init__(self) -> None:
        self.controls: dict[str, VirtualControl] = {}
        self.touches: dict[int, Vec2] = {}

    def add_button(
        self, control_id: str, rect: tuple[float, float, float, float]
    ) -> VirtualControl:
        control = VirtualControl(control_id, rect)
        self.controls[control_id] = control
        return control

    def add_joystick(
        self, control_id: str, rect: tuple[float, float, float, float]
    ) -> VirtualControl:
        return self.add_button(control_id, rect)

    def touch_down(self, finger: int, position: Vec2) -> None:
        self.touches[finger] = position.copy()
        self._update_controls()

    def touch_move(self, finger: int, position: Vec2) -> None:
        if finger in self.touches:
            self.touches[finger] = position.copy()
            self._update_controls()

    def touch_up(self, finger: int) -> None:
        self.touches.pop(finger, None)
        self._update_controls()

    def _update_controls(self) -> None:
        points = tuple(self.touches.values())
        for control in self.controls.values():
            point = next((point for point in points if control.contains(point)), None)
            control.pressed = point is not None
            if point is None:
                control.value = Vec2()
                continue
            x, y, width, height = control.rect
            control.value = Vec2(
                clamp((point.x - x) / width * 2 - 1, -1, 1),
                clamp((point.y - y) / height * 2 - 1, -1, 1),
            )
