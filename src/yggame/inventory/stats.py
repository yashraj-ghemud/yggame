# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Combat statistics, modifiers, damage packets, and status effects."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from yggame.core.events import EventBus


class ModifierMode(Enum):
    ADD = "add"
    MULTIPLY = "multiply"
    OVERRIDE = "override"


@dataclass(frozen=True, slots=True)
class Modifier:
    stat: str
    amount: float
    mode: ModifierMode = ModifierMode.ADD
    source: str = ""
    priority: int = 0


@dataclass(slots=True)
class Stat:
    name: str
    base: float = 0.0
    minimum: float | None = None
    maximum: float | None = None
    modifiers: list[Modifier] = field(default_factory=list)

    def value(self) -> float:
        overrides = sorted(
            (item for item in self.modifiers if item.mode is ModifierMode.OVERRIDE),
            key=lambda item: item.priority,
        )
        result = overrides[-1].amount if overrides else self.base
        result += sum(item.amount for item in self.modifiers if item.mode is ModifierMode.ADD)
        multiplier = 1.0
        for item in sorted(
            (item for item in self.modifiers if item.mode is ModifierMode.MULTIPLY),
            key=lambda item: item.priority,
        ):
            multiplier *= item.amount
        result *= multiplier
        if self.minimum is not None:
            result = max(self.minimum, result)
        if self.maximum is not None:
            result = min(self.maximum, result)
        return result

    def add(self, modifier: Modifier) -> None:
        self.modifiers.append(modifier)

    def remove_source(self, source: str) -> None:
        self.modifiers[:] = [item for item in self.modifiers if item.source != source]


class StatBlock:
    def __init__(self, definitions: Iterable[Stat] = ()) -> None:
        self.stats: dict[str, Stat] = {stat.name: stat for stat in definitions}

    def define(
        self,
        name: str,
        base: float = 0.0,
        *,
        minimum: float | None = None,
        maximum: float | None = None,
    ) -> Stat:
        if name in self.stats:
            raise ValueError(f"duplicate stat: {name}")
        stat = Stat(name, base, minimum, maximum)
        self.stats[name] = stat
        return stat

    def get(self, name: str) -> Stat:
        try:
            return self.stats[name]
        except KeyError as exc:
            raise KeyError(f"unknown stat: {name}") from exc

    def value(self, name: str, default: float | None = None) -> float:
        return (
            self.stats[name].value()
            if name in self.stats
            else (default if default is not None else 0.0)
        )

    def add_modifier(self, modifier: Modifier) -> None:
        self.get(modifier.stat).add(modifier)

    def remove_source(self, source: str) -> None:
        for stat in self.stats.values():
            stat.remove_source(source)

    def snapshot(self) -> dict[str, float]:
        return {name: stat.value() for name, stat in self.stats.items()}


class DamageType(Enum):
    PHYSICAL = "physical"
    FIRE = "fire"
    ICE = "ice"
    ELECTRIC = "electric"
    POISON = "poison"
    TRUE = "true"


@dataclass(frozen=True, slots=True)
class DamagePacket:
    amount: float
    damage_type: DamageType = DamageType.PHYSICAL
    source: Any = None
    critical: bool = False
    tags: frozenset[str] = frozenset()

    def scaled(self, multiplier: float) -> DamagePacket:
        return DamagePacket(
            self.amount * multiplier, self.damage_type, self.source, self.critical, self.tags
        )


@dataclass(frozen=True, slots=True)
class DamageResult:
    incoming: DamagePacket
    mitigated: float
    absorbed: float
    lethal: bool
    remaining_health: float


class Health:
    def __init__(self, maximum: float, *, events: EventBus | None = None) -> None:
        if maximum <= 0:
            raise ValueError("health maximum must be positive")
        self.maximum = maximum
        self.current = maximum
        self.events = events or EventBus()
        self.dead = False

    @property
    def fraction(self) -> float:
        return max(0.0, min(1.0, self.current / self.maximum))

    def heal(self, amount: float, *, source: Any = None) -> float:
        if amount < 0:
            raise ValueError("heal amount cannot be negative")
        previous = self.current
        self.current = min(self.maximum, self.current + amount)
        healed = self.current - previous
        if healed:
            self.events.emit("healed", {"amount": healed, "source": source}, source=self)
        return healed

    def apply(
        self, packet: DamagePacket, *, mitigation: float = 0.0, absorption: float = 0.0
    ) -> DamageResult:
        if mitigation < 0 or absorption < 0:
            raise ValueError("mitigation and absorption cannot be negative")
        incoming = max(0.0, packet.amount)
        mitigated = incoming * max(0.0, 1.0 - mitigation)
        absorbed = min(mitigated, absorption)
        damage = max(0.0, mitigated - absorbed)
        self.current = max(0.0, self.current - damage)
        lethal = self.current <= 0 and not self.dead
        if lethal:
            self.dead = True
        result = DamageResult(packet, damage, absorbed, lethal, self.current)
        self.events.emit("damage_taken", result, source=self)
        if lethal:
            self.events.emit("death", result, source=self)
        return result

    def revive(self, value: float | None = None) -> None:
        self.current = min(self.maximum, value if value is not None else self.maximum)
        self.dead = False
        self.events.emit("revived", {"health": self.current}, source=self)


@dataclass(slots=True)
class StatusEffect:
    id: str
    duration: float
    stacks: int = 1
    maximum_stacks: int = 1
    tick_interval: float = 1.0
    elapsed: float = 0.0
    tick_elapsed: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.duration <= 0 or self.tick_interval <= 0 or self.maximum_stacks <= 0:
            raise ValueError("status effect duration and intervals must be positive")
        self.stacks = max(1, min(self.maximum_stacks, self.stacks))

    @property
    def expired(self) -> bool:
        return self.elapsed >= self.duration

    def refresh(self, duration: float | None = None, stacks: int = 1) -> None:
        self.elapsed = 0.0
        self.stacks = min(self.maximum_stacks, self.stacks + stacks)
        if duration is not None:
            self.duration = duration

    def update(self, delta: float) -> int:
        self.elapsed += max(0.0, delta)
        self.tick_elapsed += max(0.0, delta)
        ticks = 0
        while self.tick_elapsed >= self.tick_interval and not self.expired:
            self.tick_elapsed -= self.tick_interval
            ticks += 1
        return ticks


class StatusController:
    def __init__(self, *, events: EventBus | None = None) -> None:
        self.events = events or EventBus()
        self.effects: dict[str, StatusEffect] = {}

    def apply(self, effect: StatusEffect) -> StatusEffect:
        existing = self.effects.get(effect.id)
        if existing:
            existing.refresh(effect.duration, effect.stacks)
            target = existing
        else:
            self.effects[effect.id] = effect
            target = effect
        self.events.emit("status_applied", target, source=self)
        return target

    def remove(self, effect_id: str) -> StatusEffect | None:
        removed = self.effects.pop(effect_id, None)
        if removed:
            self.events.emit("status_removed", removed, source=self)
        return removed

    def update(self, delta: float) -> list[StatusEffect]:
        expired: list[StatusEffect] = []
        for effect in tuple(self.effects.values()):
            ticks = effect.update(delta)
            for _ in range(ticks):
                self.events.emit("status_tick", effect, source=self)
            if effect.expired:
                expired.append(effect)
        for effect in expired:
            self.remove(effect.id)
        return expired

    def has(self, effect_id: str) -> bool:
        return effect_id in self.effects
