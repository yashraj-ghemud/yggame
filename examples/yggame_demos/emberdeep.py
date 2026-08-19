# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Emberdeep: a seeded roguelike dungeon vertical slice."""

from __future__ import annotations

import random
from dataclasses import dataclass

from yggame.core import RecoveryManager
from yggame.inventory import (
    DamagePacket,
    Equipment,
    Health,
    Inventory,
    Item,
    ItemStack,
    LootEntry,
    LootTable,
    Modifier,
    ModifierMode,
    StatBlock,
)
from yggame.world import BSPDungeon, TileDefinition, TileLayer, Tilemap

from .base import DemoCommand, seeded_stream, status_score_message


@dataclass(slots=True)
class DungeonEnemy:
    name: str
    health: Health
    damage: float


class Emberdeep:
    name = "Emberdeep"

    def __init__(self, seed: int = 7) -> None:
        self.reset(seed)

    def reset(self, seed: int) -> None:
        self.seed = seed
        self.stream = seeded_stream(seed, "emberdeep")
        self.rng = random.Random(seed)
        self.status = "running"
        self.score = 0
        self.step_count = 0
        self.floor = 1
        self.room_index = 0
        self.explored = 0
        self.gold = 0
        self.player_health = Health(12)
        self.stats = StatBlock()
        self.stats.define("attack", 3.0, minimum=1.0)
        self.stats.define("armor", 0.0, minimum=0.0)
        self.inventory = Inventory(8)
        self.equipment = Equipment(("weapon", "armor"))
        self.items = {
            "ember": Item(
                "ember", "A warm ember used for crafting.", max_stack=20, rarity="common"
            ),
            "iron_sword": Item(
                "iron_sword", "A reliable blade.", rarity="rare", tags=frozenset({"weapon"})
            ),
            "ash_mail": Item(
                "ash_mail",
                "Armor forged in volcanic ash.",
                rarity="rare",
                tags=frozenset({"armor"}),
            ),
            "potion": Item(
                "potion",
                "Restores health.",
                max_stack=5,
                rarity="common",
                tags=frozenset({"consumable"}),
            ),
        }
        self.loot = LootTable(
            (
                LootEntry(self.items["ember"], 5, 1, 3),
                LootEntry(self.items["potion"], 2),
                LootEntry(self.items["iron_sword"], 1),
                LootEntry(self.items["ash_mail"], 1),
            )
        )
        self.inventory.add(self.items["potion"], 2)
        self.recovery = RecoveryManager(maximum=5)
        self.dungeon = BSPDungeon(48, 32, seed=seed + self.floor, minimum_room=5)
        self.rooms = self.dungeon.generate(splits=5)
        self.map = Tilemap(48, 32, 16)
        self.map.registry.register(TileDefinition(1, "floor", tags=frozenset({"walkable"})))
        self.map.registry.register(TileDefinition(2, "wall", solid=True, tags=frozenset({"solid"})))
        self.map.add_layer(TileLayer("terrain", 48, 32, default=2))
        self.enemy: DungeonEnemy | None = None
        self.pending_loot: ItemStack | None = None

    def default_commands(self) -> tuple[DemoCommand, ...]:
        return tuple(
            DemoCommand.parse(item)
            for item in (
                "explore",
                "fight",
                "loot",
                "explore",
                "fight",
                "loot",
                "equip weapon",
                "descend",
                "explore",
                "fight",
                "loot",
                "use potion",
                "save",
                "descend",
                "explore",
                "fight",
            )
        )

    def step(self, command: DemoCommand):
        if self.status != "running":
            return status_score_message(self, f"dungeon run already {self.status}")
        self.step_count += 1
        changed: list[str] = []
        if command.name in {"explore", "move", "search"}:
            self.explored += 1
            self.room_index += 1
            self.score += 10
            if self.enemy is None and self.room_index % 2 == 0:
                elite = self.room_index % 4 == 0
                self.enemy = DungeonEnemy(
                    "Ash Warden" if elite else "Cinderling",
                    Health(8 if elite else 4),
                    2.0 if elite else 1.0,
                )
                changed.append("enemy")
            else:
                changed.append("room")
        elif command.name in {"fight", "attack"}:
            if self.enemy is None:
                return status_score_message(self, "No enemy waits in this room.")
            result = self.enemy.health.apply(
                DamagePacket(self.stats.value("attack"), source="hero"), mitigation=0
            )
            if result.lethal:
                self.score += 75
                self.pending_loot = self.loot.roll(self.rng)
                self.enemy = None
                changed.extend(("defeated", "loot-ready"))
            else:
                incoming = max(0.0, self.enemy.damage - self.stats.value("armor"))
                hurt = self.player_health.apply(DamagePacket(incoming, source=self.enemy.name))
                changed.append("damage")
                if hurt.lethal:
                    self.status = "lost"
                    return status_score_message(
                        self, "The Emberdeep claimed another explorer.", tuple(changed)
                    )
        elif command.name == "loot":
            if self.pending_loot is None:
                return status_score_message(self, "There is no unclaimed loot here.")
            added = self.inventory.add(self.pending_loot.item, self.pending_loot.quantity)
            if added:
                self.score += 50
                changed.append(self.pending_loot.item.id)
                self.pending_loot = None
            else:
                changed.append("inventory-full")
        elif command.name == "equip":
            slot = command.argument or "weapon"
            item = self.items.get("iron_sword" if slot == "weapon" else "ash_mail")
            if item and self.inventory.count(item.id):
                self.equipment.equip(slot, item)
                self.inventory.remove(item.id)
                if slot == "weapon":
                    self.stats.add_modifier(
                        Modifier("attack", 3, ModifierMode.ADD, source="iron_sword")
                    )
                else:
                    self.stats.add_modifier(
                        Modifier("armor", 1, ModifierMode.ADD, source="ash_mail")
                    )
                changed.append(slot)
        elif command.name == "use" and command.argument == "potion":
            if self.inventory.remove("potion"):
                self.player_health.heal(4)
                changed.append("healed")
        elif command.name == "save":
            self.recovery.checkpoint("floor", self._state())
            changed.append("checkpoint")
        elif command.name == "descend":
            if self.enemy is not None:
                return status_score_message(self, "Defeat the room guardian before descending.")
            self.floor += 1
            self.score += 100
            self.dungeon = BSPDungeon(48, 32, seed=self.seed + self.floor, minimum_room=5)
            self.rooms = self.dungeon.generate(splits=5)
            self.room_index = 0
            changed.append("floor")
            if self.floor >= 3:
                self.status = "won"
                self.score += self.player_health.current * 10
                return status_score_message(
                    self, "The core of Emberdeep is reached.", tuple(changed + ["victory"])
                )
        return status_score_message(
            self,
            f"floor={self.floor} room={self.room_index} hp={self.player_health.current:.0f}",
            tuple(changed),
        )

    def _state(self) -> dict[str, object]:
        return {
            "floor": self.floor,
            "room": self.room_index,
            "score": self.score,
            "gold": self.gold,
            "health": self.player_health.current,
            "inventory": [stack.item.id for stack in self.inventory.slots if stack],
        }

    def summary(self) -> str:
        carried = sum(stack.quantity for stack in self.inventory.slots if stack)
        return (
            f"Emberdeep — {self.status}; floor={self.floor}; score={self.score}; "
            f"hp={self.player_health.current:.0f}; carried={carried}"
        )

    def render_text(self) -> str:
        room_total = max(1, len(self.rooms))
        inventory = ", ".join(stack.item.name for stack in self.inventory.slots if stack) or "empty"
        return (
            f"EMBERDEEP\nFloor {self.floor}  Room {self.room_index}/{room_total}\n"
            f"HP: {self.player_health.current:.0f}/12  "
            f"Attack: {self.stats.value('attack'):.0f}  Armor: {self.stats.value('armor'):.0f}\n"
            f"Inventory: {inventory}"
        )
