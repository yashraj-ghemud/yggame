# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Data-driven inventory and item systems designed for headless testing."""

from __future__ import annotations

import random
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class Item:
    id: str
    name: str
    description: str = ""
    max_stack: int = 1
    rarity: str = "common"
    tags: frozenset[str] = frozenset()
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id or self.max_stack <= 0:
            raise ValueError("items require an id and a positive max_stack")


class ItemDatabase:
    def __init__(self) -> None:
        self._items: dict[str, Item] = {}

    def register(self, item: Item) -> Item:
        if item.id in self._items:
            raise ValueError(f"duplicate item id: {item.id}")
        self._items[item.id] = item
        return item

    def get(self, item_id: str) -> Item:
        return self._items[item_id]

    def load(self, definitions: Iterable[dict[str, Any]]) -> None:
        for definition in definitions:
            self.register(
                Item(
                    id=definition["id"],
                    name=definition["name"],
                    description=definition.get("description", ""),
                    max_stack=definition.get("max_stack", 1),
                    rarity=definition.get("rarity", "common"),
                    tags=frozenset(definition.get("tags", ())),
                    metadata=dict(definition.get("metadata", {})),
                )
            )


@dataclass(slots=True)
class ItemStack:
    item: Item
    quantity: int = 1

    def __post_init__(self) -> None:
        if not 0 < self.quantity <= self.item.max_stack:
            raise ValueError("stack quantity must be within the item's stack limits")


class Inventory:
    """Slot inventory with atomic add/remove operations."""

    def __init__(self, capacity: int) -> None:
        if capacity <= 0:
            raise ValueError("inventory capacity must be positive")
        self.slots: list[ItemStack | None] = [None] * capacity

    @property
    def capacity(self) -> int:
        return len(self.slots)

    def count(self, item_id: str) -> int:
        return sum(stack.quantity for stack in self.slots if stack and stack.item.id == item_id)

    def can_add(self, item: Item, quantity: int = 1) -> bool:
        if quantity <= 0:
            return False
        remaining = quantity
        for stack in self.slots:
            if stack is None:
                remaining -= item.max_stack
            elif stack.item.id == item.id:
                remaining -= item.max_stack - stack.quantity
            if remaining <= 0:
                return True
        return False

    def add(self, item: Item, quantity: int = 1) -> int:
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        if not self.can_add(item, quantity):
            return 0
        remaining = quantity
        for stack in self.slots:
            if stack and stack.item.id == item.id and stack.quantity < item.max_stack:
                moved = min(remaining, item.max_stack - stack.quantity)
                stack.quantity += moved
                remaining -= moved
        for index, stack in enumerate(self.slots):
            if remaining <= 0:
                break
            if stack is None:
                moved = min(remaining, item.max_stack)
                self.slots[index] = ItemStack(item, moved)
                remaining -= moved
        return quantity - remaining

    def remove(self, item_id: str, quantity: int = 1) -> bool:
        if quantity <= 0 or self.count(item_id) < quantity:
            return False
        remaining = quantity
        for index, stack in enumerate(self.slots):
            if stack and stack.item.id == item_id:
                removed = min(remaining, stack.quantity)
                stack.quantity -= removed
                remaining -= removed
                if stack.quantity == 0:
                    self.slots[index] = None
                if remaining == 0:
                    break
        return True

    def move(self, source: int, target: int) -> None:
        if not (0 <= source < self.capacity and 0 <= target < self.capacity):
            raise IndexError("inventory slot outside bounds")
        if source == target:
            return
        first, second = self.slots[source], self.slots[target]
        if first and second and first.item.id == second.item.id:
            moved = min(first.quantity, first.item.max_stack - second.quantity)
            second.quantity += moved
            first.quantity -= moved
            if first.quantity == 0:
                self.slots[source] = None
        else:
            self.slots[source], self.slots[target] = second, first


@dataclass(frozen=True, slots=True)
class StatModifier:
    stat: str
    amount: float
    mode: str = "add"


class Equipment:
    def __init__(self, slots: Iterable[str]) -> None:
        self._items: dict[str, Item] = {}
        self._slots = frozenset(slots)

    def equip(self, slot: str, item: Item) -> Item | None:
        if slot not in self._slots:
            raise KeyError(f"unknown equipment slot: {slot}")
        previous = self._items.get(slot)
        self._items[slot] = item
        return previous

    def unequip(self, slot: str) -> Item | None:
        return self._items.pop(slot, None)

    def get(self, slot: str) -> Item | None:
        return self._items.get(slot)

    def modifiers(self) -> list[StatModifier]:
        result: list[StatModifier] = []
        for item in self._items.values():
            result.extend(item.metadata.get("modifiers", ()))
        return result


@dataclass(frozen=True, slots=True)
class Recipe:
    id: str
    ingredients: dict[str, int]
    output: ItemStack


class Crafting:
    @staticmethod
    def can_craft(inventory: Inventory, recipe: Recipe) -> bool:
        if not all(
            inventory.count(item_id) >= quantity for item_id, quantity in recipe.ingredients.items()
        ):
            return False
        # Ingredients may occupy full stacks. Evaluate output capacity after the
        # exact ingredient removal without mutating the caller's inventory.
        simulated = Inventory(inventory.capacity)
        simulated.slots = [
            ItemStack(stack.item, stack.quantity) if stack is not None else None
            for stack in inventory.slots
        ]
        for item_id, quantity in recipe.ingredients.items():
            simulated.remove(item_id, quantity)
        return simulated.can_add(recipe.output.item, recipe.output.quantity)

    @staticmethod
    def craft(inventory: Inventory, recipe: Recipe) -> bool:
        if not Crafting.can_craft(inventory, recipe):
            return False
        for item_id, quantity in recipe.ingredients.items():
            if not inventory.remove(item_id, quantity):
                raise RuntimeError("inventory changed during crafting transaction")
        if inventory.add(recipe.output.item, recipe.output.quantity) != recipe.output.quantity:
            raise RuntimeError("inventory lost output capacity during crafting transaction")
        return True


@dataclass(frozen=True, slots=True)
class LootEntry:
    item: Item
    weight: float
    minimum: int = 1
    maximum: int = 1


class LootTable:
    def __init__(self, entries: Iterable[LootEntry]) -> None:
        self.entries = tuple(entries)
        if not self.entries or any(entry.weight <= 0 for entry in self.entries):
            raise ValueError("loot tables require positive-weight entries")

    def roll(self, rng: random.Random | None = None) -> ItemStack:
        picker = rng or random
        entry = picker.choices(self.entries, weights=[item.weight for item in self.entries], k=1)[0]
        quantity = picker.randint(entry.minimum, entry.maximum)
        return ItemStack(entry.item, quantity)
