# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Keyboard/gamepad focus navigation for accessible retained-mode interfaces."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum

from .base import UIElement, UIEvent, UIManager


class NavigationDirection(Enum):
    NEXT = "next"
    PREVIOUS = "previous"
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"


@dataclass(frozen=True, slots=True)
class FocusPolicy:
    wrap: bool = True
    prefer_spatial: bool = True
    consume_navigation_events: bool = True


class FocusGroup:
    """Maintains deterministic focus order for a subset of UI elements."""

    def __init__(
        self,
        manager: UIManager,
        elements: Iterable[UIElement] = (),
        *,
        policy: FocusPolicy | None = None,
    ) -> None:
        self.manager = manager
        self.policy = policy or FocusPolicy()
        self.elements: list[UIElement] = []
        self.index = -1
        self.set_elements(elements)

    def set_elements(self, elements: Iterable[UIElement]) -> None:
        self.elements = [
            element
            for element in elements
            if element.visible and element.enabled and element.focusable
        ]
        self.index = min(self.index, len(self.elements) - 1)

    @property
    def current(self) -> UIElement | None:
        return self.elements[self.index] if 0 <= self.index < len(self.elements) else None

    def focus(self, index: int) -> UIElement | None:
        if not self.elements:
            self.index = -1
            self.manager.set_focus(None)
            return None
        if self.policy.wrap:
            index %= len(self.elements)
        else:
            index = max(0, min(index, len(self.elements) - 1))
        self.index = index
        self.manager.set_focus(self.elements[index])
        return self.elements[index]

    def move(self, direction: NavigationDirection) -> UIElement | None:
        if direction is NavigationDirection.NEXT:
            return self.focus(self.index + 1 if self.index >= 0 else 0)
        if direction is NavigationDirection.PREVIOUS:
            return self.focus(self.index - 1 if self.index >= 0 else len(self.elements) - 1)
        if not self.elements:
            return None
        current = self.current or self.elements[0]
        if direction in {
            NavigationDirection.UP,
            NavigationDirection.DOWN,
            NavigationDirection.LEFT,
            NavigationDirection.RIGHT,
        }:
            candidate = self._spatial(current, direction)
            if candidate is not None:
                self.index = self.elements.index(candidate)
                self.manager.set_focus(candidate)
                return candidate
        return self.current

    def handle(self, event: UIEvent) -> bool:
        mapping = {
            "tab": NavigationDirection.NEXT,
            "shift+tab": NavigationDirection.PREVIOUS,
            "up": NavigationDirection.UP,
            "down": NavigationDirection.DOWN,
            "left": NavigationDirection.LEFT,
            "right": NavigationDirection.RIGHT,
        }
        direction = mapping.get(event.key or "") if event.type == "key_down" else None
        if direction is None:
            return False
        self.move(direction)
        if self.policy.consume_navigation_events:
            event.consume()
        return True

    def _spatial(self, current: UIElement, direction: NavigationDirection) -> UIElement | None:
        center = current.rect.center
        candidates: list[tuple[float, UIElement]] = []
        for element in self.elements:
            if element is current:
                continue
            delta = element.rect.center - center
            if direction is NavigationDirection.UP and delta.y >= 0:
                continue
            if direction is NavigationDirection.DOWN and delta.y <= 0:
                continue
            if direction is NavigationDirection.LEFT and delta.x >= 0:
                continue
            if direction is NavigationDirection.RIGHT and delta.x <= 0:
                continue
            distance = delta.length_squared
            candidates.append((distance, element))
        return min(candidates, key=lambda item: item[0])[1] if candidates else None


class FocusTrap:
    """Keeps focus inside a modal subtree until released."""

    def __init__(self, manager: UIManager, root: UIElement) -> None:
        self.manager = manager
        self.root = root
        self.previous = manager.focused
        self.active = False

    def activate(self) -> None:
        self.active = True
        focusable = self._focusable(self.root)
        if focusable:
            self.manager.set_focus(focusable[0])

    def release(self) -> None:
        self.active = False
        self.manager.set_focus(self.previous)

    def enforce(self) -> None:
        if self.active and self.manager.focused not in self._focusable(self.root):
            focusable = self._focusable(self.root)
            self.manager.set_focus(focusable[0] if focusable else None)

    @staticmethod
    def _focusable(root: UIElement) -> list[UIElement]:
        result = [root] if root.focusable and root.visible and root.enabled else []
        for child in root.children:
            result.extend(FocusTrap._focusable(child))
        return result
