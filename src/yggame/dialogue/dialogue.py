# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Headless branching dialogue and quest primitives."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

Condition = Callable[[dict[str, Any]], bool]


@dataclass(frozen=True, slots=True)
class Choice:
    text: str
    target: str
    condition: Condition | None = None
    effects: tuple[Callable[[dict[str, Any]], None], ...] = ()

    def available(self, state: dict[str, Any]) -> bool:
        return self.condition is None or self.condition(state)


@dataclass(frozen=True, slots=True)
class DialogueNode:
    id: str
    speaker: str
    text: str
    next_node: str | None = None
    choices: tuple[Choice, ...] = ()
    tags: frozenset[str] = frozenset()


class DialogueTree:
    def __init__(self, nodes: list[DialogueNode], start: str) -> None:
        self.nodes = {node.id: node for node in nodes}
        if start not in self.nodes:
            raise ValueError(f"dialogue start node does not exist: {start}")
        self.start = start

    def get(self, node_id: str) -> DialogueNode:
        return self.nodes[node_id]

    def available_choices(self, node_id: str, state: dict[str, Any]) -> tuple[Choice, ...]:
        return tuple(choice for choice in self.get(node_id).choices if choice.available(state))


class DialogueSession:
    def __init__(self, tree: DialogueTree, *, state: dict[str, Any] | None = None) -> None:
        self.tree = tree
        self.state = state if state is not None else {}
        self.current_id = tree.start
        self.finished = False

    @property
    def current(self) -> DialogueNode:
        return self.tree.get(self.current_id)

    def advance(self) -> DialogueNode | None:
        if self.finished:
            return None
        if self.current.choices:
            raise RuntimeError("dialogue node requires a choice")
        if self.current.next_node is None:
            self.finished = True
            return None
        self.current_id = self.current.next_node
        return self.current

    def choose(self, index: int) -> DialogueNode:
        choices = self.tree.available_choices(self.current_id, self.state)
        if not (0 <= index < len(choices)):
            raise IndexError("dialogue choice outside available choices")
        choice = choices[index]
        for effect in choice.effects:
            effect(self.state)
        self.current_id = choice.target
        return self.current


@dataclass(slots=True)
class Objective:
    id: str
    description: str
    required: int = 1
    progress: int = 0
    complete: bool = False

    def advance(self, amount: int = 1) -> bool:
        self.progress = min(self.required, self.progress + amount)
        self.complete = self.progress >= self.required
        return self.complete


@dataclass(slots=True)
class Quest:
    id: str
    title: str
    objectives: list[Objective]
    rewards: dict[str, Any] = field(default_factory=dict)
    active: bool = False
    completed: bool = False

    def start(self) -> None:
        self.active = True

    def update_objective(self, objective_id: str, amount: int = 1) -> bool:
        if not self.active or self.completed:
            return False
        objective = next((item for item in self.objectives if item.id == objective_id), None)
        if objective is None:
            raise KeyError(f"unknown quest objective: {objective_id}")
        objective.advance(amount)
        self.completed = all(item.complete for item in self.objectives)
        return self.completed


class QuestSystem:
    def __init__(self) -> None:
        self.quests: dict[str, Quest] = {}

    def register(self, quest: Quest) -> None:
        if quest.id in self.quests:
            raise ValueError(f"duplicate quest id: {quest.id}")
        self.quests[quest.id] = quest

    def activate(self, quest_id: str) -> Quest:
        quest = self.quests[quest_id]
        quest.start()
        return quest

    def signal(self, objective_id: str, amount: int = 1) -> list[Quest]:
        completed: list[Quest] = []
        for quest in self.quests.values():
            was_complete = quest.completed
            quest.update_objective(objective_id, amount)
            if quest.completed and not was_complete:
                completed.append(quest)
        return completed
