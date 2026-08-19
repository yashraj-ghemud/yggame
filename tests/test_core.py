# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

from dataclasses import dataclass

import pytest

from yggame.core import Clock, Config, EventBus, Game, Rect, Vec2, World, move_toward
from yggame.save import SaveManager


def test_vec2_and_rect_geometry() -> None:
    vector = Vec2(3, 4)
    assert vector.length == 5
    assert Rect(0, 0, 10, 10).intersects(Rect(9, 9, 2, 2))
    assert not Rect(0, 0, 10, 10).intersects(Rect(10, 0, 1, 1))
    assert move_toward(0, 10, 3) == 3


def test_event_bus_priority_once_and_stop() -> None:
    bus = EventBus()
    calls: list[str] = []
    bus.subscribe("hit", lambda event: calls.append("low"), priority=0)
    bus.once("hit", lambda event: calls.append("high"), priority=10)
    bus.subscribe("hit", lambda event: (calls.append("stop"), False)[1], priority=5)
    bus.emit("hit")
    bus.emit("hit")
    assert calls == ["high", "stop", "stop"]


def test_clock_pause_and_scale() -> None:
    clock = Clock()
    assert clock.tick(0.1) == pytest.approx(0.1)
    clock.set_time_scale(0.5)
    assert clock.tick(0.1) == pytest.approx(0.05)
    clock.pause()
    assert clock.tick(0.1) == 0


def test_ecs_stale_handles_are_rejected() -> None:
    @dataclass
    class Position:
        x: int

    world = World()
    entity = world.create(Position(4))
    assert world.get(entity, Position).x == 4
    world.destroy(entity)
    assert not world.is_alive(entity)
    with pytest.raises(KeyError):
        world.get(entity, Position)


def test_game_fixed_timestep() -> None:
    class System:
        def __init__(self) -> None:
            self.updates = 0

        def update(self, delta: float) -> None:
            self.updates += 1

        def draw(self, target, interpolation: float) -> None:
            pass

    system = System()
    game = Game(fixed_delta=0.1)
    game.add_system(system)
    frame = game.step(0.25, render=False)
    assert frame.updates == 2
    assert system.updates == 2
    game.stop()


def test_config_and_save_migration(tmp_path) -> None:
    config = Config()
    config.set("audio.master", 0.8)
    config_path = tmp_path / "settings.json"
    config.save(config_path)
    assert Config.load(config_path).get("audio.master") == 0.8

    manager = SaveManager(
        schema=2, game_version="1.0", migrations={1: lambda payload: {**payload, "new": True}}
    )
    save_path = tmp_path / "save.json"
    SaveManager(schema=1, game_version="0.9").save(save_path, {"score": 5})
    assert manager.load(save_path) == {"score": 5, "new": True}
