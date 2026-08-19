# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Theme tokens shared by UI components and render adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import cast

from yggame.render.text import Color, TextStyle


@dataclass(frozen=True, slots=True)
class Palette:
    background: Color = Color(24, 28, 38)
    surface: Color = Color(40, 46, 62)
    surface_hover: Color = Color(54, 62, 82)
    surface_pressed: Color = Color(28, 33, 46)
    text: Color = Color(240, 243, 250)
    text_muted: Color = Color(167, 175, 193)
    accent: Color = Color(88, 166, 255)
    success: Color = Color(77, 205, 128)
    warning: Color = Color(245, 190, 77)
    danger: Color = Color(238, 96, 96)
    outline: Color = Color(88, 101, 128)


@dataclass(frozen=True, slots=True)
class Typography:
    body: TextStyle = TextStyle()
    heading: TextStyle = TextStyle(bold=True)
    caption: TextStyle = TextStyle(color=Color(167, 175, 193))
    button: TextStyle = TextStyle(bold=True)
    monospace: TextStyle = TextStyle()


@dataclass(frozen=True, slots=True)
class Spacing:
    unit: float = 4.0
    small: float = 4.0
    medium: float = 8.0
    large: float = 16.0
    xlarge: float = 24.0


@dataclass(slots=True)
class Theme:
    palette: Palette = field(default_factory=Palette)
    typography: Typography = field(default_factory=Typography)
    spacing: Spacing = field(default_factory=Spacing)
    radius: float = 6.0
    border_width: float = 1.0
    metrics: dict[str, float] = field(default_factory=dict)

    def color(self, name: str, fallback: Color | None = None) -> Color:
        value = getattr(self.palette, name, fallback)
        if value is None:
            raise KeyError(f"unknown theme color: {name}")
        return value

    def text_style(self, name: str = "body") -> TextStyle:
        try:
            return cast(TextStyle, getattr(self.typography, name))
        except AttributeError as exc:
            raise KeyError(f"unknown text style: {name}") from exc

    def set_metric(self, name: str, value: float) -> None:
        if value < 0:
            raise ValueError("theme metrics cannot be negative")
        self.metrics[name] = value

    def copy(self) -> Theme:
        return Theme(
            self.palette,
            self.typography,
            self.spacing,
            self.radius,
            self.border_width,
            dict(self.metrics),
        )


DEFAULT_THEME = Theme()
