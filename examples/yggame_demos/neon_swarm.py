# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Neon Swarm: top-down arena survival built from yggame systems."""

from __future__ import annotations

from dataclasses import dataclass

from yggame.ai import SteeringAgent
from yggame.core import Rect, Vec2
from yggame.fx import ParticleConfig, ParticleSystem
from yggame.inventory import (
    DamagePacket,
    DamageType,
    Health,
    Modifier,
    ModifierMode,
    StatBlock,
    StatusController,
    StatusEffect,
)
from yggame.physics import CollisionGrid, SpatialHash, TopDownBody
from yggame.world import EncounterScheduler, EncounterWave

from .base import DemoCommand, status_score_message


@dataclass(slots=True)
class SwarmEnemy:
    id: str
    agent: SteeringAgent
    health: Health
    damage: float = 1.0
    elite: bool = False


class NeonSwarm:
    name = "Neon Swarm"

    def __init__(self, seed: int = 7) -> None:
        self.reset(seed)

    def reset(self, seed: int) -> None:
        self.seed = seed
        self.status = "running"
        self.score = 0
        self.step_count = 0
        self.player = TopDownBody(Rect(320, 180, 24, 24))
        self.health = Health(8)
        self.stats = StatBlock()
        self.stats.define("fire_rate", 1.0, minimum=0.25)
        self.stats.define("damage", 2.0, minimum=1.0)
        self.stats.define("speed", 160.0, minimum=60.0)
        self.statuses = StatusController()
        self.statuses.apply(StatusEffect("overdrive", 999, tick_interval=999))
        self.enemies: list[SwarmEnemy] = []
        self.wave = 0
        self.experience = 0
        self.level = 1
        self.shot_cooldown = 0.0
        self.damage_cooldown = 0.0
        self.arena = CollisionGrid(25, 15, 32)
        self.spatial = SpatialHash(48)
        self.particles = ParticleSystem(
            ParticleConfig(emission_rate=0, burst=5, maximum=128), seed=seed
        )
        self.waves = EncounterScheduler(
            (
                EncounterWave("wave-1", (("drone", 3, 1.0),), 0.0),
                EncounterWave("wave-2", (("drone", 4, 1.0), ("elite", 1, 0.3)), 2.0),
                EncounterWave("wave-3", (("drone", 6, 1.0), ("elite", 2, 0.5)), 3.0),
            )
        )
        self.waves.start()

    def default_commands(self) -> tuple[DemoCommand, ...]:
        return tuple(
            DemoCommand.parse(item)
            for item in (
                "move right",
                "shoot",
                "move up",
                "shoot",
                "move left",
                "shoot",
                "upgrade",
                "move down",
                "shoot",
                "move right",
                "shoot",
                "move up",
                "shoot",
                "shoot",
                "shoot",
            )
        )

    def step(self, command: DemoCommand):
        if self.status != "running":
            return status_score_message(self, f"arena already {self.status}")
        self.step_count += 1
        changed: list[str] = []
        if command.name == "move":
            vector = {
                "right": Vec2(1, 0),
                "left": Vec2(-1, 0),
                "up": Vec2(0, -1),
                "down": Vec2(0, 1),
            }.get(command.argument, Vec2())
        elif command.name in {"right", "left", "up", "down"}:
            vector = {
                "right": Vec2(1, 0),
                "left": Vec2(-1, 0),
                "up": Vec2(0, -1),
                "down": Vec2(0, 1),
            }[command.name]
        else:
            vector = Vec2()
        self.player.max_speed = self.stats.value("speed")
        self.player.update(0.25, vector)
        self.player.bounds = Rect(
            max(0, min(self.player.bounds.x, 776)),
            max(0, min(self.player.bounds.y, 456)),
            self.player.bounds.width,
            self.player.bounds.height,
        )
        self.shot_cooldown = max(0.0, self.shot_cooldown - 0.25)
        self.damage_cooldown = max(0.0, self.damage_cooldown - 0.25)
        wave = self.waves.update(0.25)
        if wave:
            self.wave += 1
            for kind, quantity, _weight in wave.entries:
                for index in range(quantity):
                    position = Vec2(
                        48 + (self.wave * 91 + index * 57) % 700, 48 + (index * 73) % 360
                    )
                    enemy = SwarmEnemy(
                        f"{wave.id}-{kind}-{index}",
                        SteeringAgent(position, maximum_speed=60 if kind == "drone" else 45),
                        Health(3 if kind == "drone" else 7),
                        elite=kind == "elite",
                    )
                    self.enemies.append(enemy)
            changed.append(wave.id)
        if command.name in {"shoot", "fire", "attack"} and self.shot_cooldown <= 0:
            target = min(
                self.enemies,
                key=lambda enemy: enemy.agent.position.distance_to(self.player.bounds.center),
                default=None,
            )
            if target and target.agent.position.distance_to(self.player.bounds.center) <= 220:
                target.health.apply(
                    DamagePacket(self.stats.value("damage"), DamageType.ELECTRIC, source="player")
                )
                self.score += 10
                self.particles.position = target.agent.position.copy()
                self.particles.burst(5)
                changed.append("hit")
            self.shot_cooldown = self.stats.value("fire_rate")
        if command.name == "upgrade" and self.experience >= 30:
            self.experience -= 30
            self.level += 1
            self.stats.add_modifier(
                Modifier("damage", 0.75, ModifierMode.ADD, source=f"level-{self.level}")
            )
            changed.append("level-up")
        for enemy in tuple(self.enemies):
            enemy.agent.seek(self.player.bounds.center, 0.25, slowing_radius=100)
            if (
                enemy.agent.position.distance_to(self.player.bounds.center) < 24
                and self.damage_cooldown <= 0
            ):
                result = self.health.apply(
                    DamagePacket(enemy.damage, DamageType.PHYSICAL, source=enemy.id)
                )
                self.damage_cooldown = 0.75
                if result.lethal:
                    self.status = "lost"
                    return status_score_message(
                        self, "The swarm overwhelmed the pilot.", tuple(changed + ["damage"])
                    )
            if enemy.health.dead:
                self.enemies.remove(enemy)
                self.experience += 10 if enemy.elite else 5
                self.score += 100 if enemy.elite else 25
                changed.append("defeated")
        self.particles.update(0.25)
        if self.wave >= 3 and not self.enemies and self.waves.finished:
            self.status = "won"
            self.score += self.health.current * 20
            return status_score_message(
                self, "The arena is clear: Neon Swarm complete.", tuple(changed + ["victory"])
            )
        return status_score_message(
            self,
            f"wave={self.wave}/3 enemies={len(self.enemies)} level={self.level}",
            tuple(changed),
        )

    def summary(self) -> str:
        return (
            f"Neon Swarm — {self.status}; score={self.score}; wave={self.wave}/3; "
            f"level={self.level}; hp={self.health.current:.0f}"
        )

    def render_text(self) -> str:
        return (
            f"NEON SWARM\n{'·' * 36}\n"
            f"Pilot HP: {self.health.current:.0f}/8  Enemies: {len(self.enemies)}\n"
            f"Wave: {self.wave}/3  Level: {self.level}  Score: {self.score}"
        )
