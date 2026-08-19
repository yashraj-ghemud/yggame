# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Last Bastion: tower-defense strategy vertical slice."""

from __future__ import annotations

from dataclasses import dataclass

from yggame.core import Cooldown
from yggame.inventory import DamagePacket, Health, Modifier, ModifierMode, StatBlock
from yggame.world import (
    EncounterScheduler,
    EncounterWave,
    TileDefinition,
    TileLayer,
    Tilemap,
)

from .base import DemoCommand, status_score_message


@dataclass(slots=True)
class Tower:
    id: str
    position: tuple[int, int]
    damage: float
    range: float
    cooldown: Cooldown
    shots: int = 0


@dataclass(slots=True)
class Invader:
    id: str
    position: tuple[int, int]
    path: list[tuple[int, int]]
    index: int
    health: Health
    speed: int = 1


class LastBastion:
    name = "Last Bastion"

    def __init__(self, seed: int = 7) -> None:
        self.reset(seed)

    def reset(self, seed: int) -> None:
        self.seed = seed
        self.status = "running"
        self.score = 0
        self.step_count = 0
        self.gold = 120
        self.core = Health(20)
        self.stats = StatBlock()
        self.stats.define("tower_damage", 3.0, minimum=1.0)
        self.stats.define("tower_range", 3.0, minimum=1.0)
        self.map = Tilemap(18, 10, 32)
        self.map.registry.register(TileDefinition(1, "ground", tags=frozenset({"walkable"})))
        self.map.registry.register(
            TileDefinition(2, "blocked", solid=True, tags=frozenset({"blocked"}))
        )
        self.terrain = self.map.add_layer(TileLayer("terrain", 18, 10, default=1))
        self.path = [(x, 4) for x in range(18)]
        self.start = (0, 4)
        self.goal = (17, 4)
        self.towers: dict[str, Tower] = {}
        self.invaders: list[Invader] = []
        self.wave = 0
        self.waves = EncounterScheduler(
            (
                EncounterWave("wave-1", (("scout", 4, 1.0),), 0.0),
                EncounterWave("wave-2", (("scout", 5, 1.0), ("brute", 1, 0.4)), 1.0),
                EncounterWave("wave-3", (("scout", 7, 1.0), ("brute", 2, 0.6)), 1.0),
            )
        )
        self.waves.start()

    def default_commands(self) -> tuple[DemoCommand, ...]:
        return tuple(
            DemoCommand.parse(item)
            for item in (
                "build 5,4",
                "build 8,4",
                "build 11,4",
                "wait",
                "wait",
                "wait",
                "upgrade",
                "wait",
                "wait",
                "build 14,4",
                "wait",
                "wait",
                "wait",
                "wait",
                "wait",
            )
        )

    def step(self, command: DemoCommand):
        if self.status != "running":
            return status_score_message(self, f"bastion already {self.status}")
        self.step_count += 1
        changed: list[str] = []
        if command.name == "build":
            point = self._parse_point(command.argument)
            tower_id = f"tower-{len(self.towers) + 1}"
            if point in {tower.position for tower in self.towers.values()}:
                return status_score_message(self, "That tile already contains a tower.")
            if point not in self.path or self.gold < 40:
                return status_score_message(self, "Build requires 40 gold and a path tile.")
            self.towers[tower_id] = Tower(
                tower_id,
                point,
                self.stats.value("tower_damage"),
                self.stats.value("tower_range"),
                Cooldown(1.0),
            )
            self.gold -= 40
            changed.append("tower-built")
        elif command.name == "upgrade":
            if self.gold >= 60:
                self.gold -= 60
                self.stats.add_modifier(
                    Modifier(
                        "tower_damage", 2.0, ModifierMode.ADD, source=f"upgrade-{self.step_count}"
                    )
                )
                for tower in self.towers.values():
                    tower.damage = self.stats.value("tower_damage")
                changed.append("upgraded")
        wave = self.waves.update(0.5)
        if wave:
            self.wave += 1
            for kind, quantity, _weight in wave.entries:
                for index in range(quantity):
                    hp = 7 if kind == "scout" else 18
                    self.invaders.append(
                        Invader(
                            f"{wave.id}-{kind}-{index}",
                            self.start,
                            list(self.path),
                            0,
                            Health(hp),
                            1 if kind == "scout" else 2,
                        )
                    )
            changed.append(wave.id)
        for tower in self.towers.values():
            tower.cooldown.update(0.5)
            if not tower.cooldown.ready:
                continue
            target = next(
                (
                    invader
                    for invader in self.invaders
                    if self._distance(tower.position, invader.position) <= tower.range
                ),
                None,
            )
            if target:
                result = target.health.apply(DamagePacket(tower.damage, source=tower.id))
                tower.shots += 1
                tower.cooldown.trigger()
                changed.append("shot")
                if result.lethal:
                    self.gold += 12
                    self.score += 30
                    self.invaders.remove(target)
                    changed.append("defeated")
        for invader in tuple(self.invaders):
            if invader not in self.invaders:
                continue
            if invader.index + 1 < len(invader.path):
                invader.index += invader.speed
                invader.index = min(invader.index, len(invader.path) - 1)
                invader.position = invader.path[invader.index]
            else:
                self.invaders.remove(invader)
                result = self.core.apply(DamagePacket(invader.speed, source=invader.id))
                changed.append("breach")
                if result.lethal:
                    self.status = "lost"
                    return status_score_message(
                        self, "The Last Bastion has fallen.", tuple(changed)
                    )
        if self.wave >= 3 and self.waves.finished and not self.invaders:
            self.status = "won"
            self.score += self.core.current * 25 + self.gold
            return status_score_message(
                self, "All waves defeated: Last Bastion complete.", tuple(changed + ["victory"])
            )
        return status_score_message(
            self,
            f"wave={self.wave}/3 invaders={len(self.invaders)} gold={self.gold}",
            tuple(changed),
        )

    def _parse_point(self, value: str) -> tuple[int, int]:
        try:
            x, y = (int(part.strip()) for part in value.split(",", 1))
        except ValueError as exc:
            raise ValueError("build command expects x,y") from exc
        if not (0 <= x < self.map.width and 0 <= y < self.map.height):
            raise ValueError("build point is outside the map")
        return x, y

    @staticmethod
    def _distance(a: tuple[int, int], b: tuple[int, int]) -> float:
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def summary(self) -> str:
        return (
            f"Last Bastion — {self.status}; score={self.score}; wave={self.wave}/3; "
            f"core={self.core.current:.0f}; towers={len(self.towers)}; gold={self.gold}"
        )

    def render_text(self) -> str:
        board = [["." for _ in range(self.map.width)] for _ in range(self.map.height)]
        for x, y in self.path:
            board[y][x] = "="
        for tower in self.towers.values():
            x, y = tower.position
            board[y][x] = "T"
        for invader in self.invaders:
            x, y = invader.position
            board[y][x] = "X"
        return (
            "LAST BASTION\n"
            + "\n".join("".join(row) for row in board)
            + f"\nCore: {self.core.current:.0f}/20  Gold: {self.gold}  Score: {self.score}"
        )
