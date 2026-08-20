# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""The Missing Signal: narrative detective RPG vertical slice."""

from __future__ import annotations

from yggame.content import ContentDocument, ContentRegistry, ContentType
from yggame.core import Breadcrumbs, Telemetry
from yggame.dialogue import DialogueScriptParser, DialogueSession, Objective, Quest, QuestSystem
from yggame.save import SaveManager

from .base import DemoCommand, status_score_message


class MissingSignal:
    name = "The Missing Signal"

    def __init__(self, seed: int = 7) -> None:
        self.reset(seed)

    def reset(self, seed: int) -> None:
        self.seed = seed
        self.status = "running"
        self.score = 0
        self.step_count = 0
        self.clues: set[str] = set()
        self.flags: dict[str, object] = {"has_transmitter": False, "trusted_mara": False}
        self.breadcrumbs = Breadcrumbs()
        self.telemetry = Telemetry()
        self.save_manager = SaveManager(schema=1, game_version="0.3.0")
        self.content = ContentRegistry()
        self.content.register(ContentType("clue"))
        for clue in ("burned_frequency", "dock_witness", "blueprint"):
            self.content.add(ContentDocument("clue", clue, 1, {"title": clue.replace("_", " ")}))
        self.quests = QuestSystem()
        self.case = Quest(
            "missing-signal",
            "Find the Missing Signal",
            [
                Objective("frequency", "Recover the burned frequency."),
                Objective("witness", "Interview the dock witness."),
                Objective("blueprint", "Find the transmitter blueprint."),
            ],
            rewards={"score": 500},
        )
        self.quests.register(self.case)
        self.quests.activate(self.case.id)
        script = """
        label start:
        Mara: The station went silent at midnight.
        -> Ask about the dock -> dock
        -> Ask about the transmitter -> transmitter
        label dock:
        Mara: A dock worker saw a blue light near the old relay.
        goto end
        label transmitter:
        Mara: The transmitter was moved after someone burned its frequency.
        goto end
        label end:
        Mara: Bring me proof, detective.
        """
        self.tree = DialogueScriptParser().parse(script)
        self.dialogue = DialogueSession(self.tree, state=self.flags)
        self.current_location = "station"

    def default_commands(self) -> tuple[DemoCommand, ...]:
        return tuple(
            DemoCommand.parse(item)
            for item in (
                "talk",
                "choose 0",
                "inspect dock",
                "talk",
                "choose 1",
                "inspect frequency",
                "travel relay",
                "inspect blueprint",
                "talk",
                "choose 0",
                "report",
                "save",
            )
        )

    def step(self, command: DemoCommand):
        if self.status != "running":
            return status_score_message(self, f"case already {self.status}")
        self.step_count += 1
        changed: list[str] = []
        self.breadcrumbs.add(f"step {self.step_count}: {command}")
        self.telemetry.record("command", command_name=command.name, argument=command.argument)
        if command.name == "talk":
            if self.dialogue.finished:
                self.dialogue = DialogueSession(self.tree, state=self.flags)
            changed.append("dialogue")
        elif command.name == "choose":
            try:
                choice = int(command.argument)
                node = self.dialogue.choose(choice)
            except (ValueError, IndexError, RuntimeError) as exc:
                return status_score_message(self, f"That choice is unavailable: {exc}")
            if node.id == "dock":
                self.flags["trusted_mara"] = True
            else:
                self.flags["has_transmitter"] = True
            changed.append(node.id)
        elif command.name in {"inspect", "search"}:
            clue = command.argument.strip().replace(" ", "_")
            aliases = {
                "dock": "dock_witness",
                "witness": "dock_witness",
                "frequency": "burned_frequency",
                "blueprint": "blueprint",
            }
            clue_id = aliases.get(clue, clue)
            if (
                clue_id in {"burned_frequency", "dock_witness", "blueprint"}
                and clue_id not in self.clues
            ):
                self.clues.add(clue_id)
                objective = {
                    "burned_frequency": "frequency",
                    "dock_witness": "witness",
                    "blueprint": "blueprint",
                }[clue_id]
                completed = self.quests.signal(objective)
                self.score += 100
                changed.append(clue_id)
                if completed:
                    changed.append("quest-complete")
        elif command.name == "travel":
            self.current_location = command.argument or "station"
            changed.append(self.current_location)
        elif command.name == "report":
            if self.case.completed:
                self.status = "won"
                self.score += 500
                return status_score_message(
                    self,
                    "Case closed: the Missing Signal has been recovered.",
                    tuple(changed + ["victory"]),
                )
            missing = [objective.id for objective in self.case.objectives if not objective.complete]
            return status_score_message(self, f"The case is incomplete: {', '.join(missing)}")
        elif command.name == "save":
            payload = {
                "clues": sorted(self.clues),
                "flags": dict(self.flags),
                "score": self.score,
                "location": self.current_location,
            }
            self.save_manager.save("/tmp/yggame-missing-signal.json", payload)
            changed.append("saved")
        return status_score_message(
            self, f"location={self.current_location} clues={len(self.clues)}/3", tuple(changed)
        )

    def summary(self) -> str:
        return (
            f"The Missing Signal — {self.status}; score={self.score}; "
            f"clues={len(self.clues)}/3; location={self.current_location}"
        )

    def render_text(self) -> str:
        node = self.dialogue.current
        objectives = ", ".join(
            f"{item.id}:{item.progress}/{item.required}" for item in self.case.objectives
        )
        clues = ", ".join(sorted(self.clues)) or "none"
        return (
            f"THE MISSING SIGNAL\n{node.speaker}: {node.text}\n"
            f"Location: {self.current_location}\nClues: {clues}\nQuest: {objectives}"
        )
