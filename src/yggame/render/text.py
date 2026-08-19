# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Headless rich-text layout primitives with optional Pygame rendering adapters."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

from yggame.core.geometry import Vec2


@dataclass(frozen=True, slots=True)
class Color:
    r: int
    g: int
    b: int
    a: int = 255

    def __post_init__(self) -> None:
        if any(not 0 <= value <= 255 for value in (self.r, self.g, self.b, self.a)):
            raise ValueError("color channels must be between 0 and 255")

    def with_alpha(self, alpha: int) -> Color:
        return Color(self.r, self.g, self.b, alpha)

    def as_tuple(self) -> tuple[int, int, int, int]:
        return self.r, self.g, self.b, self.a

    @classmethod
    def from_hex(cls, value: str) -> Color:
        text = value.lstrip("#")
        if len(text) not in {6, 8}:
            raise ValueError("hex colors must contain six or eight digits")
        try:
            channels = tuple(int(text[index : index + 2], 16) for index in range(0, len(text), 2))
        except ValueError as exc:
            raise ValueError(f"invalid hex color: {value!r}") from exc
        if len(channels) == 4:
            return cls(channels[0], channels[1], channels[2], channels[3])
        return cls(channels[0], channels[1], channels[2], 255)


@dataclass(frozen=True, slots=True)
class TextStyle:
    color: Color = Color(255, 255, 255)
    bold: bool = False
    italic: bool = False
    outline: int = 0
    shadow: Vec2 | None = None


@dataclass(frozen=True, slots=True)
class TextSpan:
    text: str
    style: TextStyle = TextStyle()


@dataclass(frozen=True, slots=True)
class LayoutGlyph:
    character: str
    position: Vec2
    style: TextStyle


class TextMeasurer(Protocol):
    def measure(self, text: str, style: TextStyle) -> Vec2: ...


class ApproximateMeasurer:
    """Predictable fallback measurer for headless layout and tests."""

    def __init__(self, character_width: float = 8.0, line_height: float = 16.0) -> None:
        self.character_width = character_width
        self.line_height = line_height

    def measure(self, text: str, style: TextStyle) -> Vec2:
        width = len(text) * self.character_width * (1.08 if style.bold else 1.0)
        return Vec2(width, self.line_height)


_TAG = re.compile(r"\[(?P<tag>/?(?:color|b|i|outline|shadow))(?:=(?P<value>[^\]]+))?\]")


class RichTextParser:
    """Parses a small safe markup subset into immutable spans."""

    def parse(self, text: str, base: TextStyle | None = None) -> tuple[TextSpan, ...]:
        current = base or TextStyle()
        stack: list[tuple[str, TextStyle]] = []
        spans: list[TextSpan] = []
        cursor = 0
        for match in _TAG.finditer(text):
            if match.start() > cursor:
                spans.append(TextSpan(text[cursor : match.start()], current))
            tag, value = match.group("tag"), match.group("value")
            if tag.startswith("/"):
                closing = tag[1:]
                for index in range(len(stack) - 1, -1, -1):
                    if stack[index][0] == closing:
                        _, current = stack.pop(index)
                        break
                else:
                    spans.append(TextSpan(match.group(0), current))
            else:
                stack.append((tag, current))
                current = self._apply(current, tag, value)
            cursor = match.end()
        if cursor < len(text):
            spans.append(TextSpan(text[cursor:], current))
        return tuple(span for span in spans if span.text)

    @staticmethod
    def _apply(style: TextStyle, tag: str, value: str | None) -> TextStyle:
        if tag == "b":
            return TextStyle(style.color, True, style.italic, style.outline, style.shadow)
        if tag == "i":
            return TextStyle(style.color, style.bold, True, style.outline, style.shadow)
        if tag == "color":
            if value is None:
                raise ValueError("color tag requires a value")
            return TextStyle(
                Color.from_hex(value), style.bold, style.italic, style.outline, style.shadow
            )
        if tag == "outline":
            return TextStyle(style.color, style.bold, style.italic, int(value or 1), style.shadow)
        if tag == "shadow":
            return TextStyle(style.color, style.bold, style.italic, style.outline, Vec2(2, 2))
        raise ValueError(f"unsupported rich-text tag: {tag}")


class TextLayout:
    def __init__(self, measurer: TextMeasurer | None = None) -> None:
        self.measurer = measurer or ApproximateMeasurer()

    def layout(
        self,
        spans: tuple[TextSpan, ...],
        *,
        max_width: float | None = None,
        line_spacing: float = 0.0,
    ) -> tuple[LayoutGlyph, ...]:
        if max_width is not None and max_width <= 0:
            raise ValueError("max_width must be positive")
        glyphs: list[LayoutGlyph] = []
        cursor = Vec2()
        line_height = self.measurer.measure("Ag", TextStyle()).y + line_spacing
        for span in spans:
            for character in span.text:
                if character == "\n":
                    cursor.x = 0
                    cursor.y += line_height
                    continue
                advance = self.measurer.measure(character, span.style).x
                if max_width is not None and cursor.x > 0 and cursor.x + advance > max_width:
                    cursor.x = 0
                    cursor.y += line_height
                glyphs.append(LayoutGlyph(character, cursor.copy(), span.style))
                cursor.x += advance
        return tuple(glyphs)


class Typewriter:
    def __init__(self, spans: tuple[TextSpan, ...], *, characters_per_second: float = 40.0) -> None:
        if characters_per_second <= 0:
            raise ValueError("characters_per_second must be positive")
        self.spans = spans
        self.characters_per_second = characters_per_second
        self.progress = 0.0
        self.complete = False
        self._character_count = sum(len(span.text) for span in spans)

    @property
    def visible_characters(self) -> int:
        return min(self._character_count, int(self.progress))

    def update(self, delta: float) -> None:
        self.progress = min(
            self._character_count, self.progress + max(0.0, delta) * self.characters_per_second
        )
        self.complete = self.visible_characters >= self._character_count

    def skip(self) -> None:
        self.progress = float(self._character_count)
        self.complete = True

    def visible_spans(self) -> tuple[TextSpan, ...]:
        remaining = self.visible_characters
        result: list[TextSpan] = []
        for span in self.spans:
            text = span.text[:remaining]
            if text:
                result.append(TextSpan(text, span.style))
            remaining -= len(text)
            if remaining <= 0:
                break
        return tuple(result)
