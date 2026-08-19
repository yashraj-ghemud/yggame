# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Dependency-free retained-mode UI foundation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from yggame.core.geometry import Rect, Vec2
from yggame.core.signals import SignalDispatcher


@dataclass(slots=True)
class UIEvent:
    type: str
    position: Vec2 | None = None
    key: str | None = None
    text: str | None = None
    handled: bool = False

    def consume(self) -> None:
        self.handled = True


class UIElement(SignalDispatcher):
    """Base retained UI element with parent/child tree and rectangular layout."""

    def __init__(self, rect: Rect | None = None, *, name: str = "") -> None:
        super().__init__()
        self.name = name
        self.rect = rect or Rect(0, 0, 0, 0)
        self.parent: UIElement | None = None
        self.children: list[UIElement] = []
        self.visible = True
        self.enabled = True
        self.focusable = False
        self.hovered = False
        self.focused = False
        self.z_index = 0

    def add(self, child: UIElement) -> UIElement:
        if child is self or self._contains(child):
            raise ValueError("cannot create a cycle in the UI tree")
        if child.parent:
            child.parent.remove(child)
        child.parent = self
        self.children.append(child)
        return child

    def remove(self, child: UIElement) -> None:
        self.children.remove(child)
        child.parent = None

    def _contains(self, candidate: UIElement) -> bool:
        return any(child is candidate or child._contains(candidate) for child in self.children)

    def hit_test(self, position: Vec2) -> UIElement | None:
        if not self.visible or not self.enabled or not self.rect.contains(position):
            return None
        for child in sorted(self.children, key=lambda item: item.z_index, reverse=True):
            hit = child.hit_test(position)
            if hit:
                return hit
        return self if self.focusable else None

    def handle(self, event: UIEvent) -> bool:
        if not self.visible or not self.enabled:
            return False
        self.emit_signal(f"event:{event.type}", event)
        return event.handled

    def update(self, delta: float) -> None:
        for child in tuple(self.children):
            child.update(delta)

    def draw(self, target: Any) -> None:
        for child in sorted(self.children, key=lambda item: item.z_index):
            if child.visible:
                child.draw(target)


class UIManager:
    def __init__(self, root: UIElement | None = None) -> None:
        self.root = root or UIElement(name="root")
        self.focused: UIElement | None = None
        self._hovered: UIElement | None = None

    def dispatch(self, event: UIEvent) -> UIElement | None:
        target = self.root.hit_test(event.position) if event.position else self.focused
        if event.type == "mouse_move" and target is not self._hovered:
            if self._hovered:
                self._hovered.hovered = False
                self._hovered.emit_signal("hover_exit")
            self._hovered = target
            if target:
                target.hovered = True
                target.emit_signal("hover_enter")
        if target is None:
            return None
        if event.type in {"mouse_down", "key_down"} and target.focusable:
            self.set_focus(target)
        target.handle(event)
        return target

    def set_focus(self, element: UIElement | None) -> None:
        if element is self.focused:
            return
        if self.focused:
            self.focused.focused = False
            self.focused.emit_signal("focus_exit")
        self.focused = element
        if element:
            element.focused = True
            element.emit_signal("focus_enter")

    def update(self, delta: float) -> None:
        self.root.update(delta)

    def draw(self, target: Any) -> None:
        self.root.draw(target)
