# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""yggame: composable, testable 2D game-development components.

The top-level package stays intentionally small. Import subsystem APIs from their
namespaces, for example `from yggame.physics import PlatformerBody`.
"""

from .core import Game, GameContext, Rect, Vec2

__version__ = "0.3.0"
__author__ = "Yashraj Sachin Ghemud"

__all__ = ["Game", "GameContext", "Rect", "Vec2", "__version__", "__author__"]
