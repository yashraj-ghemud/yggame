# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Writer-friendly dialogue script parser with validation diagnostics.

The syntax is intentionally small and deterministic:

    label intro:
    narrator: Welcome to town.
    -> Ask about the quest [has_quest] -> quest
    * give_gold 10
    -> End -> end

Blank lines and comments beginning with `#` are ignored. The parser produces the
same DialogueTree model used by the runtime session, so writers can validate text
without running a game.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .dialogue import Choice, DialogueNode, DialogueTree


@dataclass(frozen=True, slots=True)
class ScriptDiagnostic:
    line: int
    message: str
    severity: str = "error"


@dataclass(frozen=True, slots=True)
class ScriptCommand:
    name: str
    arguments: tuple[str, ...] = ()


@dataclass(slots=True)
class _NodeBuilder:
    id: str
    speaker: str = ""
    text: str = ""
    next_node: str | None = None
    choices: list[Choice] | None = None
    commands: list[ScriptCommand] | None = None


_LABEL = re.compile(r"^label\s+(?P<name>[A-Za-z_][\w-]*):\s*$")
_LINE = re.compile(r"^(?P<speaker>[A-Za-z_][\w-]*):\s*(?P<text>.+)$")
_CHOICE = re.compile(
    r"^->\s*(?P<text>.+?)\s*->\s*(?P<target>[A-Za-z_][\w-]*)(?:\s*\[(?P<condition>[^\]]+)\])?$"
)
_COMMAND = re.compile(r"^\*\s*(?P<name>[A-Za-z_][\w-]*)(?:\s+(?P<args>.*))?$")
_JUMP = re.compile(r"^goto\s+(?P<target>[A-Za-z_][\w-]*)$")


class DialogueScriptParser:
    """Parse scripts into a tree and collect all diagnostics instead of failing early."""

    def __init__(
        self, *, condition_factory: Callable[[str], Callable[[dict[str, Any]], bool]] | None = None
    ) -> None:
        self.condition_factory = condition_factory or self._default_condition
        self.diagnostics: list[ScriptDiagnostic] = []

    def parse(self, text: str, *, start: str | None = None) -> DialogueTree:
        self.diagnostics.clear()
        builders: list[_NodeBuilder] = []
        current: _NodeBuilder | None = None
        for line_number, raw in enumerate(text.splitlines(), 1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            label = _LABEL.match(line)
            if label:
                if current:
                    builders.append(current)
                current = _NodeBuilder(label.group("name"), choices=[], commands=[])
                continue
            if current is None:
                self._error(line_number, "content appears before the first label")
                continue
            dialogue = _LINE.match(line)
            if dialogue:
                if current.text:
                    self._error(line_number, "a dialogue node may only have one speaker line")
                current.speaker = dialogue.group("speaker")
                current.text = dialogue.group("text")
                continue
            choice = _CHOICE.match(line)
            if choice:
                condition = choice.group("condition")
                current.choices = current.choices or []
                current.choices.append(
                    Choice(
                        choice.group("text"),
                        choice.group("target"),
                        self.condition_factory(condition) if condition else None,
                    )
                )
                continue
            command = _COMMAND.match(line)
            if command:
                args = tuple(command.group("args").split()) if command.group("args") else ()
                current.commands = current.commands or []
                current.commands.append(ScriptCommand(command.group("name"), args))
                continue
            jump = _JUMP.match(line)
            if jump:
                current.next_node = jump.group("target")
                continue
            self._error(line_number, f"unrecognized syntax: {line}")
        if current:
            builders.append(current)
        nodes = self._build_nodes(builders)
        if self.diagnostics:
            raise DialogueScriptError(tuple(self.diagnostics))
        if not nodes:
            raise DialogueScriptError((ScriptDiagnostic(1, "script contains no labels"),))
        return DialogueTree(nodes, start or nodes[0].id)

    def validate(self, text: str) -> tuple[ScriptDiagnostic, ...]:
        try:
            self.parse(text)
        except DialogueScriptError as exc:
            return exc.diagnostics
        return ()

    def _build_nodes(self, builders: list[_NodeBuilder]) -> list[DialogueNode]:
        known = {builder.id for builder in builders}
        nodes: list[DialogueNode] = []
        for index, builder in enumerate(builders):
            if not builder.speaker or not builder.text:
                self._error(index + 1, f"label {builder.id!r} has no speaker line")
            choices = tuple(builder.choices or ())
            for choice in choices:
                if choice.target not in known:
                    self._error(index + 1, f"choice points to unknown label {choice.target!r}")
            next_node = builder.next_node
            if next_node is None and not choices and index + 1 < len(builders):
                next_node = builders[index + 1].id
            if next_node is not None and next_node not in known:
                self._error(index + 1, f"jump points to unknown label {next_node!r}")
            nodes.append(
                DialogueNode(builder.id, builder.speaker, builder.text, next_node, choices)
            )
        return nodes

    def _error(self, line: int, message: str) -> None:
        self.diagnostics.append(ScriptDiagnostic(line, message))

    @staticmethod
    def _default_condition(expression: str) -> Callable[[dict[str, Any]], bool]:
        key = expression.strip()
        if not key:
            return lambda _state: True
        if key.startswith("!"):
            name = key[1:]
            return lambda state: not bool(state.get(name))
        return lambda state: bool(state.get(key))


class DialogueScriptError(ValueError):
    def __init__(self, diagnostics: tuple[ScriptDiagnostic, ...]) -> None:
        self.diagnostics = diagnostics
        message = "; ".join(f"line {item.line}: {item.message}" for item in diagnostics)
        super().__init__(message)
