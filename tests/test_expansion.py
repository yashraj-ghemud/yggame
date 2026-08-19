# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

from dataclasses import dataclass

import pytest

from yggame.core import (
    CodecRegistry,
    ConfigurationError,
    Replay,
    ReplayRecorder,
    ResourceManager,
    Schema,
    SystemGraph,
    SystemSpec,
    Vec2,
    dumps,
    one_of,
)
from yggame.core.geometry import Rect
from yggame.render import Color, RichTextParser, TextLayout, Typewriter
from yggame.ui import (
    Checkbox,
    Direction,
    Dropdown,
    Insets,
    SelectOption,
    Stack,
    TextInputField,
    ToastQueue,
)


def test_codec_handles_geometry_and_custom_dataclass() -> None:
    @dataclass(frozen=True)
    class Point:
        value: int

    registry = CodecRegistry()
    registry.register(
        Point,
        "test.Point",
        lambda point: {"value": point.value},
        lambda payload: Point(payload["value"]),
    )
    document = {"position": Vec2(2, 3), "point": Point(4)}
    restored = registry.decode(registry.encode(document))
    assert restored["position"] == Vec2(2, 3)
    assert restored["point"] == Point(4)
    encoded_color = dumps({"color": Color(1, 2, 3)})
    assert '"r": 1' in encoded_color and '"a": 255' in encoded_color


def test_resource_scope_disposes_after_last_reference() -> None:
    disposed: list[str] = []
    manager = ResourceManager()
    with manager.scope():
        first = manager.acquire("texture", lambda: "atlas", disposer=disposed.append)
        second = manager.acquire("texture", lambda: "wrong", disposer=disposed.append)
        assert first.value == second.value == "atlas"
        first.release()
        assert manager.loaded("texture")
        second.release()
    assert disposed == ["atlas"]
    assert not manager.loaded("texture")


def test_system_graph_orders_dependencies_and_detects_cycle() -> None:
    calls: list[str] = []
    graph = SystemGraph()
    graph.add(SystemSpec("render", lambda _: calls.append("render"), after=frozenset({"gameplay"})))
    graph.add(SystemSpec("gameplay", lambda _: calls.append("gameplay")))
    graph.update(0.1)
    assert calls == ["gameplay", "render"]
    graph.add(SystemSpec("cycle", lambda _: None, after=frozenset({"render"})))
    graph._systems["render"] = SystemSpec("render", lambda _: None, after=frozenset({"cycle"}))
    with pytest.raises(RuntimeError):
        graph.order()


def test_replay_round_trip() -> None:
    recorder = ReplayRecorder(seed=7)
    recorder.record(0, 1 / 60, held={"jump"}, axes={"move": 0.5})
    recorder.record(1, 1 / 60, pressed={"fire"})
    replay = Replay.from_json(recorder.replay.to_json())
    assert replay.seed == 7
    assert replay.frames[0].held == ("jump",)
    assert list(replay)[1].pressed == ("fire",)


def test_schema_defaults_and_enum_validation() -> None:
    schema = Schema(
        "settings",
        [
            __import__("yggame").core.Field("volume", float, default=1.0),
            __import__("yggame").core.Field(
                "mode", str, required=True, validator=one_of("windowed", "fullscreen")
            ),
        ],
    )
    assert schema.validate({"mode": "windowed"})["volume"] == 1.0
    with pytest.raises(ConfigurationError):
        schema.validate({"mode": "invalid"})


def test_rich_text_layout_and_typewriter() -> None:
    spans = RichTextParser().parse("Hello [color=#ff0000]world[/color]")
    assert spans[1].style.color == Color(255, 0, 0)
    glyphs = TextLayout().layout(spans, max_width=40)
    assert glyphs[-1].position.y > 0
    typewriter = Typewriter(spans, characters_per_second=100)
    typewriter.update(1)
    assert typewriter.complete


def test_ui_layout_and_interactions() -> None:
    stack = Stack(Direction.VERTICAL, Rect(0, 0, 100, 100), padding=Insets.all(4), gap=2)
    first = Checkbox("One")
    second = Checkbox("Two")
    stack.add(first)
    stack.add(second)
    stack.update(0.0)
    assert first.rect.y < second.rect.y
    first.toggle()
    assert first.value

    dropdown = Dropdown([SelectOption("a", "A"), SelectOption("b", "B")])
    dropdown.select(1)
    assert dropdown.selected is not None and dropdown.selected.value == "b"

    field = TextInputField("ab", max_length=3)
    field.focused = True
    field.handle(__import__("yggame").ui.UIEvent("text_input", text="c"))
    field.handle(__import__("yggame").ui.UIEvent("text_input", text="d"))
    assert field.text == "abc"

    queue = ToastQueue(maximum=1)
    queue.push("first")
    queue.push("second")
    assert [item.message for item in queue.messages] == ["second"]
