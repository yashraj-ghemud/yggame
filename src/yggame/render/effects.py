# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Renderer-neutral post-processing effect descriptors.

The library stores effect parameters as validated data. A Pygame or shader adapter can
translate these descriptors into actual surface operations without coupling gameplay
to a rendering backend.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from yggame.core.geometry import clamp

from .text import Color


class BlendMode(Enum):
    NORMAL = "normal"
    ADD = "add"
    MULTIPLY = "multiply"
    SCREEN = "screen"
    SUBTRACT = "subtract"


@dataclass(frozen=True, slots=True)
class Effect:
    enabled: bool = True
    strength: float = 1.0
    blend: BlendMode = BlendMode.NORMAL

    def __post_init__(self) -> None:
        if not 0 <= self.strength <= 1:
            raise ValueError("effect strength must be between zero and one")


@dataclass(frozen=True, slots=True)
class VignetteEffect(Effect):
    color: Color = Color(0, 0, 0)
    radius: float = 0.75
    softness: float = 0.35

    def __post_init__(self) -> None:
        super().__post_init__()
        if not 0 < self.radius <= 1 or not 0 <= self.softness <= 1:
            raise ValueError("vignette radius or softness is outside its range")


@dataclass(frozen=True, slots=True)
class FlashEffect(Effect):
    color: Color = Color(255, 255, 255)
    duration: float = 0.1
    elapsed: float = 0.0

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.duration <= 0 or self.elapsed < 0:
            raise ValueError("flash duration and elapsed time are invalid")

    @property
    def opacity(self) -> float:
        return self.strength * max(0.0, 1.0 - self.elapsed / self.duration)


@dataclass(frozen=True, slots=True)
class BlurEffect(Effect):
    radius: int = 4
    passes: int = 1

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.radius < 0 or self.passes <= 0:
            raise ValueError("blur radius must be non-negative and passes positive")


@dataclass(frozen=True, slots=True)
class ChromaticAberrationEffect(Effect):
    offset: float = 2.0
    angle_degrees: float = 0.0

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.offset < 0:
            raise ValueError("chromatic aberration offset cannot be negative")


@dataclass(frozen=True, slots=True)
class ColorGradeEffect(Effect):
    brightness: float = 0.0
    contrast: float = 1.0
    saturation: float = 1.0
    tint: Color = Color(255, 255, 255)

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.contrast < 0 or self.saturation < 0:
            raise ValueError("contrast and saturation cannot be negative")


@dataclass(frozen=True, slots=True)
class OutlineEffect(Effect):
    color: Color = Color(255, 255, 255)
    thickness: int = 1
    threshold: int = 16

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.thickness < 1 or self.threshold < 0:
            raise ValueError("outline thickness must be positive and threshold non-negative")


@dataclass(frozen=True, slots=True)
class CRTOverlayEffect(Effect):
    scanline_strength: float = 0.2
    curvature: float = 0.0
    noise: float = 0.05

    def __post_init__(self) -> None:
        super().__post_init__()
        if (
            not 0 <= self.scanline_strength <= 1
            or not 0 <= self.curvature <= 1
            or not 0 <= self.noise <= 1
        ):
            raise ValueError("CRT parameters must be between zero and one")


@dataclass(slots=True)
class EffectStack:
    effects: list[Effect] = field(default_factory=list)

    def add(self, effect: Effect) -> None:
        self.effects.append(effect)

    def remove(self, effect_type: type[Effect]) -> None:
        self.effects[:] = [effect for effect in self.effects if not isinstance(effect, effect_type)]

    def enabled(self) -> tuple[Effect, ...]:
        return tuple(effect for effect in self.effects if effect.enabled and effect.strength > 0)

    def replace(self, effect: Effect) -> None:
        self.remove(type(effect))
        self.add(effect)

    def clear(self) -> None:
        self.effects.clear()


@dataclass(frozen=True, slots=True)
class RenderTarget:
    width: int
    height: int
    name: str = "target"
    texture: Any = None

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("render target dimensions must be positive")

    @property
    def aspect_ratio(self) -> float:
        return self.width / self.height

    def resize(self, width: int, height: int) -> RenderTarget:
        return RenderTarget(width, height, self.name, self.texture)


def normalize_effect_strength(value: float) -> float:
    return clamp(value, 0.0, 1.0)
