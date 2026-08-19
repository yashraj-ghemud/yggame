# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Common UI widgets with sensible defaults and signal-based interaction."""

from __future__ import annotations

from yggame.core.geometry import Rect, clamp

from .base import UIElement, UIEvent


class Button(UIElement):
    def __init__(self, text: str, rect: Rect | None = None) -> None:
        super().__init__(rect or Rect(0, 0, 140, 40), name=text)
        self.text = text
        self.focusable = True
        self.pressed = False
        self.on("event:mouse_down", self._mouse_down)
        self.on("event:mouse_up", self._mouse_up)
        self.on("event:key_down", self._key_down)

    def _mouse_down(self, event: UIEvent) -> None:
        if event.position and self.rect.contains(event.position):
            self.pressed = True
            event.consume()

    def _mouse_up(self, event: UIEvent) -> None:
        if self.pressed:
            self.pressed = False
            if event.position and self.rect.contains(event.position):
                self.emit_signal("clicked", self)
            event.consume()

    def _key_down(self, event: UIEvent) -> None:
        if event.key in {"enter", "space"}:
            self.emit_signal("clicked", self)
            event.consume()


class ProgressBar(UIElement):
    def __init__(self, maximum: float = 1.0, value: float = 1.0, rect: Rect | None = None) -> None:
        super().__init__(rect or Rect(0, 0, 200, 20))
        if maximum <= 0:
            raise ValueError("progress maximum must be positive")
        self.maximum = maximum
        self.value = clamp(value, 0, maximum)
        self.display_value = self.value
        self.smoothing = 12.0

    @property
    def fraction(self) -> float:
        return self.value / self.maximum

    def set_value(self, value: float) -> None:
        previous = self.value
        self.value = clamp(value, 0, self.maximum)
        if previous != self.value:
            self.emit_signal("changed", self.value, previous)

    def update(self, delta: float) -> None:
        super().update(delta)
        amount = 1.0 if self.smoothing <= 0 else min(1.0, self.smoothing * max(0.0, delta))
        self.display_value += (self.value - self.display_value) * amount


class HealthBar(ProgressBar):
    def __init__(
        self, maximum: float = 100.0, value: float | None = None, rect: Rect | None = None
    ) -> None:
        super().__init__(maximum, maximum if value is None else value, rect)
        self.damage_flash = 0.0
        self.on("changed", self._on_changed)

    def _on_changed(self, current: float, previous: float) -> None:
        if current < previous:
            self.damage_flash = 0.12
            self.emit_signal("damaged", previous - current)
        if current <= 0:
            self.emit_signal("depleted")

    def update(self, delta: float) -> None:
        super().update(delta)
        self.damage_flash = max(0.0, self.damage_flash - max(0.0, delta))


class Slider(UIElement):
    def __init__(
        self,
        minimum: float = 0.0,
        maximum: float = 1.0,
        value: float = 0.0,
        rect: Rect | None = None,
    ) -> None:
        super().__init__(rect or Rect(0, 0, 200, 24))
        if maximum <= minimum:
            raise ValueError("slider maximum must be greater than minimum")
        self.minimum, self.maximum = minimum, maximum
        self.value = clamp(value, minimum, maximum)
        self.focusable = True

    @property
    def fraction(self) -> float:
        return (self.value - self.minimum) / (self.maximum - self.minimum)

    def set_value(self, value: float) -> None:
        previous = self.value
        self.value = clamp(value, self.minimum, self.maximum)
        if previous != self.value:
            self.emit_signal("changed", self.value, previous)

    def handle(self, event: UIEvent) -> bool:
        if event.type == "mouse_down" and event.position and self.rect.contains(event.position):
            fraction = (event.position.x - self.rect.x) / self.rect.width
            self.set_value(self.minimum + clamp(fraction, 0, 1) * (self.maximum - self.minimum))
            event.consume()
        return super().handle(event)


__all__ = ["Button", "HealthBar", "ProgressBar", "Slider"]
