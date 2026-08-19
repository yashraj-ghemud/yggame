# Five yggame Demo Games

## Purpose

These demos prove that yggame can support different gameplay genres through the same headless-first contracts. Each game is implemented as a deterministic simulation with a small command-line presentation layer. The gameplay code does not depend on a display, mixer, or network connection, so the same models can later be connected to Pygame or another frontend.

| Demo | Category | Core loop | Primary yggame systems |
| --- | --- | --- | --- |
| **Skybound Runner** | Platformer action | Run, jump, collect relics, survive hazards, reach the exit | `Game`, `InputMap`, `PlatformerBody`, `CollisionGrid`, `Camera2D`, `Health`, `ParticleSystem`, `SceneManager` |
| **Neon Swarm** | Top-down arena survival | Move, auto-fire, kite enemies, collect experience, level up, survive waves | `TopDownBody`, `SpatialHash`, `SteeringAgent`, `VisionCone`, `DamagePacket`, `Health`, `StatusController`, `ParticleSystem`, `EncounterScheduler` |
| **Emberdeep** | Roguelike dungeon crawler | Explore seeded rooms, fight, loot, equip, descend through floors, save checkpoints | `BSPDungeon`, `RandomStream`, `Tilemap`, `Inventory`, `LootTable`, `StatBlock`, `SaveSlots`, `RecoveryManager` |
| **Last Bastion** | Tower-defense strategy | Place towers, schedule waves, target enemies, spend resources, defend the core | `Tilemap`, `AStar`, `EncounterScheduler`, `Cooldown`, `SpatialHash`, `Health`, `StatBlock`, `UI` widgets |
| **The Missing Signal** | Narrative detective RPG | Inspect clues, choose dialogue, satisfy conditions, update quest objectives, resolve cases | `DialogueScriptParser`, `DialogueSession`, `QuestSystem`, `ContentRegistry`, `SaveManager`, `Localization`, `SceneManager`, `Telemetry` |

## Shared demo contract

Every demo exposes a small class with `reset()`, `step(command)`, `run(commands)`, `summary()`, and `render_text()` methods. `step()` advances one deterministic gameplay turn or fixed simulation slice. Commands are plain strings or typed command records. This keeps the game loops easy to test and makes it straightforward to add Pygame input adapters later.

The shared runner accepts a demo name, a deterministic seed, a maximum step count, and an optional scripted command sequence. It prints a compact status view, final score/progression, and a replayable command transcript. A demo can therefore be launched independently or used in CI as a smoke-test scenario.

## Quality criteria

The five demos must use yggame APIs directly in gameplay code, not merely import the package. Each must have deterministic seeded behavior, a meaningful win or loss condition, a non-trivial state transition, a text-mode presentation, and regression tests for its central loop. A game is not considered complete if it only constructs objects without exercising them.

## Implementation boundaries

The demos are deliberately scoped as polished vertical slices rather than full commercial games. They will include enough systems to demonstrate architecture, progression, and replayable behavior. Optional graphical frontends remain a follow-up layer; no demo will pretend that a headless simulation is a finished Pygame production.
