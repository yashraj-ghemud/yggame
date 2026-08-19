# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Skybound Runner: a compact platformer vertical slice built on yggame."""

from __future__ import annotations

from yggame.camera import Camera2D
from yggame.core import Rect, Vec2
from yggame.fx import ParticleConfig, ParticleSystem
from yggame.input import InputMap
from yggame.inventory import DamagePacket, Health
from yggame.physics import CollisionGrid, PlatformerBody

from .base import DemoCommand, DemoResult, id_for, seeded_stream, status_score_message


class SkyboundRunner:
    name = "Skybound Runner"

    def __init__(self, seed: int = 7) -> None:
        self.reset(seed)

    def reset(self, seed: int) -> None:
        self.seed = seed
        self.stream = seeded_stream(seed, "skybound")
        self.status = "running"
        self.score = 0
        self.step_count = 0
        self.relics = 0
        self.damage_cooldown = 0.0
        self.controls = InputMap()
        self.controls.bind("left", "keyboard:a")
        self.controls.bind("right", "keyboard:d")
        self.controls.bind("jump", "keyboard:space")
        self.grid = CollisionGrid(42, 16, 32)
        for x in range(42):
            self.grid.set_solid(x, 14)
        for x in (8, 15, 23, 31, 37):
            self.grid.set_solid(x, 12)
            self.grid.set_solid(x + 1, 12)
        self.player = PlatformerBody(Rect(48, 320, 22, 38))
        self.health = Health(3)
        self.camera = Camera2D(
            Rect(0, 0, 640, 360), position=Vec2(320, 180), bounds=Rect(0, 0, 1344, 512)
        )
        self.camera.follow(Vec2(48, 320))
        self.relic_positions = {
            id_for(seed, "relic", index): Vec2(160 + index * 180, 360 - (index % 2) * 64)
            for index in range(5)
        }
        self.hazards = [Rect(350, 416, 64, 32), Rect(800, 416, 96, 32)]
        self.exit = Rect(1260, 352, 40, 64)
        self.particles = ParticleSystem(
            ParticleConfig(emission_rate=0, burst=4, maximum=24), seed=seed
        )
        self.transcript: list[str] = []

    def default_commands(self) -> tuple[DemoCommand, ...]:
        return tuple(
            DemoCommand.parse(item)
            for item in (
                "right",
                "right",
                "jump",
                "right",
                "right",
                "jump",
                "right",
                "right",
                "right",
                "jump",
                "right",
                "right",
                "right",
                "right",
                "right",
            )
        )

    def step(self, command: DemoCommand) -> DemoResult:
        if self.status != "running":
            return status_score_message(self, f"run already {self.status}")
        self.step_count += 1
        self.transcript.append(str(command))
        horizontal = 0.0
        if command.name in {"left", "a"}:
            horizontal = -1.0
        elif command.name in {"right", "d", "run"}:
            horizontal = 1.0
        if command.name in {"jump", "space"}:
            self.player.request_jump()
        if command.name == "wait":
            horizontal = 0.0
        self.player.update(1 / 15, horizontal, self.grid)
        self.camera.target = self.player.bounds.center
        self.camera.update(1 / 15)
        self.damage_cooldown = max(0.0, self.damage_cooldown - 1 / 15)
        changed: list[str] = []
        for relic_id, position in tuple(self.relic_positions.items()):
            if self.player.bounds.contains(position):
                self.relic_positions.pop(relic_id)
                self.relics += 1
                self.score += 100
                self.particles.position = position.copy()
                self.particles.burst(4)
                changed.append("relic")
        if self.damage_cooldown <= 0 and any(
            self.player.bounds.intersects(hazard) for hazard in self.hazards
        ):
            result = self.health.apply(DamagePacket(1))
            self.damage_cooldown = 1.0
            self.camera.shake.add(0.3)
            changed.append("damage")
            if result.lethal:
                self.status = "lost"
                return status_score_message(self, "The runner fell into a hazard.", tuple(changed))
        self.particles.update(1 / 15)
        if self.player.bounds.intersects(self.exit) and self.relics >= 3:
            self.status = "won"
            self.score += 500
            return status_score_message(
                self, "The beacon opens: Skybound Runner complete.", tuple(changed + ["exit"])
            )
        return status_score_message(
            self, f"running at x={self.player.bounds.x:.0f}, relics={self.relics}/5", tuple(changed)
        )

    def summary(self) -> str:
        return (
            f"Skybound Runner — {self.status}; score={self.score}; "
            f"relics={self.relics}/5; x={self.player.bounds.x:.0f}"
        )

    def render_text(self) -> str:
        width = 42
        player_x = min(width - 1, max(0, int(self.player.bounds.center.x / 32)))
        exit_x = min(width - 1, int(self.exit.center.x / 32))
        line = ["."] * width
        line[player_x] = "P"
        line[exit_x] = "E"
        return (
            "".join(line)
            + f"\n{'=' * width}\n"
            f"HP: {self.health.current:.0f}  Relics: {self.relics}/5  Score: {self.score}"
        )
