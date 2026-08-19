# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

from __future__ import annotations

from yggame_demos.base import DemoCommand
from yggame_demos.bastion import LastBastion
from yggame_demos.emberdeep import Emberdeep
from yggame_demos.missing_signal import MissingSignal
from yggame_demos.neon_swarm import NeonSwarm
from yggame_demos.runner import all_specs, create, load_specs
from yggame_demos.skybound_runner import SkyboundRunner


def test_registry_exposes_five_categories() -> None:
    load_specs()
    specs = all_specs()
    assert len(specs) == 5
    assert {spec.category for spec in specs} == {
        "platformer action",
        "top-down arena survival",
        "roguelike dungeon crawler",
        "tower-defense strategy",
        "narrative detective RPG",
    }


def test_all_demos_accept_default_scripts_deterministically() -> None:
    load_specs()
    for spec in all_specs():
        first = create(spec.key, 17)
        second = create(spec.key, 17)
        commands = first.default_commands()[:8]
        first_results = [first.step(command).message for command in commands]
        second_results = [second.step(command).message for command in commands]
        assert first_results == second_results
        assert first.summary().startswith(spec.title)
        assert first.render_text()


def test_skybound_collects_relics_and_uses_camera() -> None:
    game = SkyboundRunner(3)
    result = game.step(DemoCommand.parse("right"))
    assert result.status == "running"
    assert game.camera.target is not None
    assert game.player.bounds.x > 48


def test_neon_swarm_spawns_waves_and_supports_upgrades() -> None:
    game = NeonSwarm(3)
    for _ in range(8):
        game.step(DemoCommand.parse("shoot"))
    assert game.wave >= 1
    assert game.enemies
    game.experience = 30
    game.step(DemoCommand.parse("upgrade"))
    assert game.level == 2


def test_emberdeep_explores_fights_and_checkpoints() -> None:
    game = Emberdeep(3)
    game.step(DemoCommand.parse("explore"))
    game.step(DemoCommand.parse("explore"))
    assert game.enemy is not None
    for _ in range(4):
        game.step(DemoCommand.parse("fight"))
    game.step(DemoCommand.parse("save"))
    assert game.recovery.latest("floor") is not None


def test_bastion_builds_towers_and_schedules_waves() -> None:
    game = LastBastion(3)
    game.step(DemoCommand.parse("build 5,4"))
    assert len(game.towers) == 1
    for _ in range(5):
        game.step(DemoCommand.parse("wait"))
    assert game.wave >= 1
    assert game.score >= 0


def test_missing_signal_can_close_the_case() -> None:
    game = MissingSignal(3)
    commands = (
        "talk",
        "choose 0",
        "inspect dock",
        "talk",
        "choose 1",
        "inspect frequency",
        "travel relay",
        "inspect blueprint",
        "report",
    )
    for raw in commands:
        game.step(DemoCommand.parse(raw))
    assert game.status == "won"
    assert len(game.clues) == 3
