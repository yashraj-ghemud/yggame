# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Headless platformer composition example.

Run with `python examples/platformer_core.py` after installing yggame in editable mode.
It intentionally uses no display so the same gameplay logic can run in tests or a
Pygame adapter.
"""

from yggame import Game, Rect
from yggame.core import BaseSystem
from yggame.input import InputMap
from yggame.physics import CollisionGrid, PlatformerBody
from yggame.ui import HealthBar


class PlatformerDemo(BaseSystem):
    def __init__(self) -> None:
        super().__init__()
        self.controls = InputMap()
        self.controls.bind("left", "keyboard:a")
        self.controls.bind("right", "keyboard:d")
        self.controls.bind("jump", "keyboard:space")
        self.grid = CollisionGrid(40, 16, 32)
        for x in range(40):
            self.grid.set_solid(x, 14)
        self.player = PlatformerBody(Rect(64, 120, 24, 40))
        self.health = HealthBar(100)

    def update(self, delta: float) -> None:
        snapshot = self.controls.update()
        horizontal = float(snapshot.is_down("right")) - float(snapshot.is_down("left"))
        if snapshot.was_pressed("jump"):
            self.player.request_jump()
        self.player.update(delta, horizontal, self.grid)
        self.health.update(delta)

    def draw(self, target, interpolation: float = 0.0) -> None:
        # A Pygame-specific renderer can consume player.bounds and health.fraction.
        pass


if __name__ == "__main__":
    game = Game()
    game.add_system(PlatformerDemo())
    game.run(frames=5, frame_source=lambda: 1 / 60)
    print("platformer simulation completed")
