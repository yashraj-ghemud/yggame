# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Responsive UI layout containers."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from yggame.core.geometry import Rect, Vec2

from .base import UIElement


class Direction(Enum):
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"


@dataclass(frozen=True, slots=True)
class Insets:
    left: float = 0.0
    top: float = 0.0
    right: float = 0.0
    bottom: float = 0.0

    @classmethod
    def all(cls, value: float) -> Insets:
        if value < 0:
            raise ValueError("insets cannot be negative")
        return cls(value, value, value, value)

    @property
    def horizontal(self) -> float:
        return self.left + self.right

    @property
    def vertical(self) -> float:
        return self.top + self.bottom


class Container(UIElement):
    def __init__(
        self,
        rect: Rect | None = None,
        *,
        padding: Insets | None = None,
        gap: float = 0.0,
        name: str = "",
    ) -> None:
        super().__init__(rect, name=name)
        self.padding = padding or Insets()
        self.gap = max(0.0, gap)

    def content_rect(self) -> Rect:
        return Rect(
            self.rect.x + self.padding.left,
            self.rect.y + self.padding.top,
            max(0.0, self.rect.width - self.padding.horizontal),
            max(0.0, self.rect.height - self.padding.vertical),
        )


class Stack(Container):
    def __init__(
        self,
        direction: Direction = Direction.VERTICAL,
        rect: Rect | None = None,
        *,
        padding: Insets | None = None,
        gap: float = 0.0,
        name: str = "",
    ) -> None:
        super().__init__(rect, padding=padding, gap=gap, name=name)
        self.direction = direction
        self.justify = "start"
        self.align = "start"

    def layout_children(self) -> None:
        content = self.content_rect()
        visible = [child for child in self.children if child.visible]
        if not visible:
            return
        main_size = content.width if self.direction is Direction.HORIZONTAL else content.height
        used = sum(
            child.rect.width if self.direction is Direction.HORIZONTAL else child.rect.height
            for child in visible
        )
        remaining = max(0.0, main_size - used - self.gap * max(0, len(visible) - 1))
        cursor = content.x if self.direction is Direction.HORIZONTAL else content.y
        if self.justify == "center":
            cursor += remaining / 2
        elif self.justify == "end":
            cursor += remaining
        elif self.justify == "space-between" and len(visible) > 1:
            gap = self.gap + remaining / (len(visible) - 1)
        else:
            gap = self.gap
        for child in visible:
            width, height = child.rect.width, child.rect.height
            if self.direction is Direction.HORIZONTAL:
                y = (
                    content.y
                    if self.align == "start"
                    else content.y + (content.height - height) / 2
                )
                if self.align == "end":
                    y = content.bottom - height
                child.rect = Rect(cursor, y, width, height)
                cursor += width + gap
            else:
                x = content.x if self.align == "start" else content.x + (content.width - width) / 2
                if self.align == "end":
                    x = content.right - width
                child.rect = Rect(x, cursor, width, height)
                cursor += height + gap

    def update(self, delta: float) -> None:
        self.layout_children()
        super().update(delta)


class Grid(Container):
    def __init__(
        self,
        columns: int,
        rect: Rect | None = None,
        *,
        row_gap: float = 0.0,
        column_gap: float = 0.0,
        padding: Insets | None = None,
        name: str = "",
    ) -> None:
        if columns <= 0:
            raise ValueError("grid columns must be positive")
        super().__init__(rect, padding=padding, name=name)
        self.columns = columns
        self.row_gap = max(0.0, row_gap)
        self.column_gap = max(0.0, column_gap)

    def layout_children(self) -> None:
        content = self.content_rect()
        width = max(0.0, (content.width - self.column_gap * (self.columns - 1)) / self.columns)
        for index, child in enumerate(self.children):
            column, row = index % self.columns, index // self.columns
            height = child.rect.height
            x = content.x + column * (width + self.column_gap)
            y = content.y + row * (height + self.row_gap)
            child.rect = Rect(x, y, width, height)

    def update(self, delta: float) -> None:
        self.layout_children()
        super().update(delta)


class Anchored(UIElement):
    def __init__(
        self,
        rect: Rect | None = None,
        *,
        anchor_min: Vec2 | None = None,
        anchor_max: Vec2 | None = None,
        offset_min: Vec2 | None = None,
        offset_max: Vec2 | None = None,
        name: str = "",
    ) -> None:
        super().__init__(rect, name=name)
        self.anchor_min = anchor_min or Vec2()
        self.anchor_max = anchor_max or self.anchor_min.copy()
        self.offset_min = offset_min or Vec2()
        self.offset_max = offset_max or self.offset_min.copy()

    def resolve(self, parent_rect: Rect) -> None:
        left = parent_rect.x + parent_rect.width * self.anchor_min.x + self.offset_min.x
        top = parent_rect.y + parent_rect.height * self.anchor_min.y + self.offset_min.y
        right = parent_rect.x + parent_rect.width * self.anchor_max.x + self.offset_max.x
        bottom = parent_rect.y + parent_rect.height * self.anchor_max.y + self.offset_max.y
        self.rect = Rect(left, top, max(0.0, right - left), max(0.0, bottom - top))

    def update(self, delta: float) -> None:
        if self.parent:
            self.resolve(self.parent.rect)
        super().update(delta)
