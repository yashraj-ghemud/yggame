# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

import pytest

from yggame.assets import AssetDependency, AssetManifest, Atlas, AtlasRegion, ContentValidator
from yggame.audio import AudioManager, AudioState
from yggame.core import EventBus, RegistrationError, Vec2
from yggame.dialogue import DialogueScriptError, DialogueScriptParser
from yggame.fx import ParticleConfig, ParticleSystem, TrailEffect
from yggame.inventory import (
    DamagePacket,
    DamageType,
    Health,
    Modifier,
    ModifierMode,
    StatBlock,
    StatusController,
    StatusEffect,
)
from yggame.net import (
    InMemoryTransport,
    Packet,
    SequenceWindow,
    Snapshot,
    SnapshotBuffer,
)
from yggame.physics import AABB, BodyState, Circle, TriggerZone, circle_circle
from yggame.plugins import PluginManager, PluginManifest
from yggame.render import (
    AnimationLibrary,
    SpriteAnimation,
    SpriteAnimator,
    SpriteFrame,
    SpriteSheet,
)
from yggame.world import (
    BSPDungeon,
    CellularCaves,
    ChunkedWorld,
    Noise2D,
    TileDefinition,
    TileLayer,
    Tilemap,
)


def test_particle_burst_and_trail_expiration() -> None:
    system = ParticleSystem(ParticleConfig(emission_rate=0, burst=4, maximum=8), seed=4)
    system.start()
    assert len(system.particles) == 0
    system.update(0.01)
    assert len(system.particles) == 4
    system.update(2.0)
    assert not system.particles
    trail = TrailEffect(lifetime=0.1)
    trail.add(Vec2(0, 0))
    trail.add(Vec2(10, 0))
    trail.update(0.11)
    assert not trail.points


def test_tilemap_and_chunk_streaming() -> None:
    tilemap = Tilemap(4, 4, 16)
    tilemap.registry.register(TileDefinition(1, "wall", solid=True))
    collision = tilemap.add_layer(TileLayer("collision", 4, 4))
    collision.set(1, 1, 1)
    assert tilemap.is_solid(1, 1)
    assert tilemap.world_to_tile(Vec2(17, 17)) == (1, 1)
    world = ChunkedWorld(4, 4, tile_size=16)
    added, removed = world.stream_around((0, 0), 1)
    assert len(added) == 9 and not removed
    assert world.get("terrain", (0, 0)) == 0


def test_procedural_generators_are_seeded() -> None:
    first = Noise2D(seed=9).sample(4, 7)
    second = Noise2D(seed=9).sample(4, 7)
    assert first == second
    caves = CellularCaves(12, 12, seed=3).generate(2)
    assert len(caves) == 12 and len(caves[0]) == 12
    dungeon = BSPDungeon(60, 40, seed=2).generate(splits=4)
    assert dungeon


def test_shape_manifold_and_trigger_events() -> None:
    manifold = circle_circle(Circle(Vec2(0, 0), 2), Circle(Vec2(3, 0), 2))
    assert manifold is not None and manifold.depth == pytest.approx(1)
    events = EventBus()
    names: list[str] = []
    events.subscribe("trigger_enter", lambda event: names.append("enter"))
    zone = TriggerZone("zone", AABB(Vec2(0, 0), Vec2(2, 2)), events=events)
    body = BodyState("player", AABB(Vec2(0, 0), Vec2(1, 1)))
    zone.update([body])
    zone.update([body])
    zone.update([])
    assert names == ["enter"]


def test_stats_health_and_status_ticks() -> None:
    stats = StatBlock()
    stats.define("power", 10)
    stats.add_modifier(Modifier("power", 5, ModifierMode.ADD, source="sword"))
    stats.add_modifier(Modifier("power", 2, ModifierMode.MULTIPLY, source="buff"))
    assert stats.value("power") == 30
    health = Health(100)
    result = health.apply(DamagePacket(25, DamageType.FIRE), mitigation=0.2)
    assert result.mitigated == pytest.approx(20)
    statuses = StatusController()
    ticks: list[str] = []
    statuses.events.subscribe("status_tick", lambda event: ticks.append(event.name))
    statuses.apply(StatusEffect("burn", 1.1, tick_interval=0.5))
    statuses.update(0.5)
    assert ticks == ["status_tick"]


def test_network_window_snapshot_and_loopback() -> None:
    window = SequenceWindow()
    assert window.accept(1)
    assert not window.accept(1)
    transport = InMemoryTransport()
    transport.connect("peer")
    packet = Packet("hello", 1, {"value": 3})
    transport.send("peer", packet)
    assert transport.receive("peer") == [packet]
    snapshots = SnapshotBuffer[float]()
    snapshots.add(Snapshot(1, 10.0, 1.0))
    snapshots.add(Snapshot(2, 20.0, 2.0))
    assert snapshots.sample(1.5, lambda a, b, amount: a + (b - a) * amount) == pytest.approx(15)


def test_plugin_dependency_order() -> None:
    manager = PluginManager()
    manager.add_manifest(PluginManifest("base", "core", "1", "math"))
    manager.add_manifest(PluginManifest("game", "combat", "1", "math", ("base.core",)))
    assert manager.activation_order() == ("base.core", "game.combat")
    manager.add_manifest(PluginManifest("cycle", "a", "1", "math", ("cycle.b",)))
    manager.add_manifest(PluginManifest("cycle", "b", "1", "math", ("cycle.a",)))
    with pytest.raises(RegistrationError):
        manager.activation_order()


def test_dialogue_script_validation() -> None:
    script = """
    label start:
    guide: Hello.
    -> Continue -> end [has_key]
    label end:
    guide: Goodbye.
    """
    tree = DialogueScriptParser().parse(script)
    assert tree.start == "start"
    assert tree.get("start").choices[0].target == "end"
    with pytest.raises(DialogueScriptError):
        DialogueScriptParser().parse("label start:\nguide: Hi\n-> Bad -> missing")


def test_atlas_animation_events_and_audio_snapshot() -> None:
    atlas = Atlas("sprites.png")
    atlas.add(AtlasRegion("idle", 0, 0, 16, 16))
    sheet = SpriteSheet(object(), width=16, height=16)
    sheet = SpriteSheet.from_atlas(object(), atlas, width=16, height=16)
    library = AnimationLibrary(sheet)
    library.add(SpriteAnimation("idle", (SpriteFrame("idle", duration=0.1, event="footstep"),)))
    animator = SpriteAnimator(library)
    animator.play("idle")
    animator.update(0.11)
    assert animator.consume_events() == ("footstep",)
    audio = AudioManager()
    state = AudioState(audio).capture()
    audio.set_volume("music", 0.2)
    AudioState(audio).restore(state)
    assert audio.buses["music"].volume == 1.0


def test_manifest_validator(tmp_path) -> None:
    manifest = AssetManifest("game")
    manifest.add(AssetDependency("missing.png", "texture"))
    issues = ContentValidator().validate_manifest(manifest, tmp_path)
    assert issues and issues[0].severity == "error"
