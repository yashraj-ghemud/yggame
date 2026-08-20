# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

> Developer and maintainer: **Yashraj Sachin Ghemud**

> This document is integrated into yggame as a production planning and implementation guide.

# yggame — 100% Production-Grade Project Prompt Pack

## 0. Product Definition

yggame is a batteries-included, modular Python game-development component library designed to sit on top of Pygame-CE. The baseline concept already covers a 20-module architecture, standalone components, shared EventBus/asset/scene integration, sensible defaults, optional ECS, plugins, templates, documentation, examples, and phased releases. Expand that foundation into a production-grade platform rather than merely a larger collection of helper classes.

### North-star outcome
Build a library that a developer can install, import, compose, test, profile, document, extend, package, and ship with. It must work for tiny prototypes and scale toward complete 2D games without forcing a single game architecture.

### Important realism constraints
- Use Pygame-CE as the default runtime/backend.
- Do not pretend Pygame has a modern GPU shader pipeline. Provide a backend abstraction and surface-based effects by default; an optional GPU/ModernGL backend may be added later.
- Multiplayer must be explicit about client/server authority, prediction, reconciliation, packet loss, versioning, and security.
- Python plugins cannot be perfectly sandboxed inside the same interpreter. Capability restrictions, manifests, subprocess isolation, and safe defaults are preferable to claiming a false security boundary.
- Every feature must degrade gracefully when optional dependencies are absent.

---

# 1. MASTER PROMPT — Paste this before every module prompt

```text
You are the lead architect, senior Python systems engineer, game-engine engineer, QA engineer, performance engineer, security reviewer, technical writer, and release engineer for the yggame project.

PROJECT:
yggame — a production-grade, modular, batteries-included game-development component library built primarily on Pygame-CE.

GOAL:
Implement the assigned module as a real production subsystem, not a demo, mock, placeholder, pseudo-code collection, or isolated toy implementation.

NON-NEGOTIABLE ENGINEERING RULES:
1. Read the existing repository before changing code.
2. Preserve existing public APIs unless a breaking change is explicitly justified.
3. Do not duplicate utilities that already exist. Reuse shared contracts.
4. Use type hints throughout public APIs and meaningful internal APIs.
5. Favor small composable classes/functions and clean interfaces.
6. Avoid hidden global state except for deliberately designed process-wide services.
7. Keep core functionality dependency-light. Optional integrations must be optional dependencies.
8. Separate runtime logic from editor/debug tooling where practical.
9. Separate data/model/backend logic from rendering/UI logic.
10. Make important systems headless-testable where possible.
11. Fail with useful exceptions and diagnostics. Never silently swallow errors.
12. Add logging at meaningful boundaries, not noisy per-frame logs by default.
13. Design for deterministic tests.
14. Avoid allocations in hot loops when practical; measure before optimizing.
15. Include cleanup/lifecycle semantics: init, start, update, render, pause/resume, shutdown/dispose.
16. Think about 30 FPS, 60 FPS, 144 FPS, low-end laptops, large entity counts, and long sessions.
17. Make serialization/versioning explicit when state is persisted.
18. Consider thread-safety/reentrancy wherever callbacks, async loading, events, or background workers exist.
19. Document what is thread-safe and what must run on the main thread.
20. Never add a security feature that is merely cosmetic. Explain the real security boundary.

ARCHITECTURE CONTRACTS:
- Shared EventBus for decoupled communication.
- Shared AssetManager/cache.
- Shared Scene/Context lifecycle.
- Shared configuration/settings system.
- Shared logging/diagnostics interfaces.
- Optional ECS, while supporting classic OOP and functional/simple approaches.
- Public APIs should be stable, discoverable, and documented.
- Avoid circular imports.
- Keep dependency direction intentional: foundational modules must not import high-level gameplay modules.

IMPLEMENTATION PROCESS — YOU MUST FOLLOW ALL 3 ITERATIONS:

ITERATION 1 — BUILD:
- Inspect repository structure, existing interfaces, coding conventions, and tests.
- Propose the module design and dependency graph.
- Implement the smallest complete production-capable version.
- Add unit tests, integration tests, and at least one real example.
- Add docs and API examples.
- Run formatting, linting, type checking, tests, and basic performance checks.

ITERATION 2 — ADVERSARIAL REVIEW:
Pretend you are a hostile reviewer trying to break this module.
Ask yourself at minimum:
- What happens if the user calls this twice?
- What happens if initialization partially fails?
- What happens during scene changes or shutdown?
- What happens with invalid inputs or corrupted data?
- What happens at 10x the expected object count?
- What happens when an asset is missing?
- What happens when an event callback raises an exception?
- What happens when frame time spikes?
- What happens when the window resizes?
- What happens when optional dependencies are missing?
- What happens when the module is used without the rest of yggame?
- Which API decisions will become painful to change later?
- Are there hidden memory leaks, stale callbacks, retained surfaces, file handles, sockets, timers, or references?
- Can the system be deterministically tested?
Fix every serious issue you discover.

ITERATION 3 — PRODUCT UPGRADE:
Now ask: “What would make this module 3x more useful than the obvious implementation?”
Add high-value features only when they fit the architecture. Examples: profiling hooks, telemetry hooks, editor integration, serialization, import/export, accessibility, mobile/controller support, validation, hot reload, caching, batching, recovery, compatibility shims, or better diagnostics.
Do not add random complexity. Every advanced feature must have a clear use case, tests, docs, and API boundaries.

SELF-CROSSQUESTIONING:
Before finalizing, answer these questions:
A. Is this genuinely reusable across different game genres?
B. Can a beginner use it with sensible defaults?
C. Can an expert deeply customize it?
D. Can it operate independently for unit tests?
E. Is the runtime path efficient?
F. Is the public API intuitive?
G. Does it integrate through existing engine contracts instead of one-off wiring?
H. Is its failure behavior predictable?
I. Is the documentation enough for someone who did not write the code?
J. What feature would users request next? Add it only if it belongs in the module.

DELIVERABLE FORMAT:
1. Architecture summary.
2. Files/classes/functions created or changed.
3. Implementation.
4. Tests.
5. Example usage.
6. Documentation.
7. Performance notes.
8. Security/reliability considerations.
9. Compatibility notes.
10. Iteration 2 findings and fixes.
11. Iteration 3 upgrades.
12. Remaining limitations and next logical integration work.

Never return “TODO”, “implement later”, fake APIs, empty methods, or screenshots pretending the feature works. If a feature is intentionally deferred, state exactly why and create the smallest stable interface needed for future integration.
```

---

# 2. MODULE 00 — Architecture, Contracts & Repository Foundation

```text
Using the MASTER PROMPT, establish the engineering foundation of yggame before implementing high-level features.

Design a scalable repository structure for a 100k+ line Python library. Define package boundaries, dependency direction, public vs private modules, naming conventions, lifecycle contracts, context objects, common protocols/interfaces, versioning policy, error hierarchy, Result-like patterns where useful, logging conventions, and compatibility strategy.

Create a central EngineContext/GameContext abstraction that provides controlled access to EventBus, AssetManager, Config, Clock, SceneManager, InputMap, Logger, and other services without forcing every component to import process-wide singletons.

Define protocols/interfaces for:
- lifecycle-aware systems
- drawable/renderable objects
- updatable systems
- serializable state
- disposable resources
- event subscribers
- asset providers
- input providers
- physics bodies
- scene lifecycle

Create strict dependency rules so core does not depend on UI, AI, networking, editor, or game-specific code.

Add architecture validation tests or tooling that can detect forbidden import cycles and forbidden dependency directions.

Create semantic versioning policy, deprecation mechanism, API stability markers, feature flags, optional dependency discovery, and compatibility helpers.

ITERATION 2: attack the architecture with circular imports, hidden global state, multiple Game instances, reinitialization, partial initialization, shutdown order, and two simultaneous game contexts.

ITERATION 3: add architecture documentation, diagrams-as-text/mermaid where useful, extension guidelines, and a minimal “build a new yggame module” internal template.

SUCCESS CRITERIA:
A future contributor should understand where new code belongs, how it communicates with the engine, how it is tested, and what it is allowed to import without reading the whole repository.
```

# 3. MODULE 01 — Core Runtime, Game Loop & Event Infrastructure

```text
Implement yggame.core as a robust runtime foundation.

Build:
- Game application lifecycle
- fixed timestep and variable timestep modes
- frame accumulator
- FPS limiting and frame pacing
- pause/resume
- time scale / slow motion
- Clock with timer/cooldown/countdown/stopwatch
- EventBus with subscribe/unsubscribe/once/priorities/weak subscriptions where appropriate
- SignalDispatcher for object-local signals
- Config/settings persistence
- ObjectPool with reset hooks and metrics
- graceful shutdown and cleanup
- exception boundaries that distinguish fatal engine errors from recoverable subsystem errors

Design EventBus carefully: define event identity, payload typing conventions, listener priority, exception isolation, subscription cleanup, and debugging traces.

Add support for custom user events without coupling to yggame's built-in event list.

Add lifecycle phases so modules can register startup/shutdown hooks in deterministic order.

ITERATION 2: test event storms, listener removal during dispatch, exceptions from handlers, recursive events, paused games, large timestep spikes, changing time scale while timers run, and object-pool misuse.

ITERATION 3: add event inspection hooks, profiling metrics, deterministic clock injection for tests, frame-time diagnostics, replay-friendly input/event capture hooks, and robust configuration migration.

Do not make developers use the event bus for everything. Direct method calls should remain possible when coupling is intentional.
```

# 4. MODULE 02 — ECS & Entity Model

```text
Implement an optional lightweight ECS that coexists with classic OOP entities and plain functions.

Build:
- Entity identifiers and generations
- component registration/storage
- add/remove/get/has component operations
- queries
- systems
- system scheduling/order
- groups/families where useful
- enable/disable entities
- entity lifetime management
- optional sparse-set or similarly efficient storage
- serialization hooks

Ensure ECS does not become mandatory. Components must be usable outside ECS when practical.

Build clear integration bridges to EventBus, Transform, Renderable, PhysicsBody, AnimationState, and other foundational protocols.

ITERATION 2: benchmark thousands/tens of thousands of entities, deletion/recreation IDs, query invalidation, iteration while mutating, and accidental component retention.

ITERATION 3: add system profiling, query caching, deterministic system scheduling, snapshot hooks, and examples showing OOP, ECS, and hybrid architectures.
```

# 5. MODULE 03 — Rendering Abstraction & Graphics Pipeline

```text
Implement yggame.render as a backend-oriented 2D renderer rather than a collection of draw helpers.

Build:
- layered/z-order renderer
- render passes
- camera transforms
- sprite batching where practical
- sprite-sheet/atlas support
- image scaling policies
- nine-patch support
- text renderer with wrapping, outlines, shadows, rich spans, typewriter support
- render targets/offscreen surfaces
- masks and clipping
- color transforms
- surface effects: vignette, flash, blur approximation, glow/outline, CRT/retro filters
- parallax layers
- render statistics

Define a Renderer interface so alternative backends can exist later. The Pygame surface backend is the default.

Optional advanced path: define—but do not require—a GPU backend interface suitable for ModernGL or another backend. Keep GPU-specific concerns out of core APIs.

ITERATION 2: attack texture lifetime, resize handling, alpha formats, repeated scaling, huge images, render-target leaks, z-order conflicts, nested clipping, and effect stacking.

ITERATION 3: add batching metrics, cache policies, pixel-perfect mode, configurable scaling policies, screenshot/export hooks, and visual regression-test infrastructure.
```

# 6. MODULE 04 — Asset Pipeline & Resource Management

```text
Build yggame.assets as a real asset lifecycle system.

Support centralized loading/caching for images, fonts, sounds, music, tilemaps, animation data, JSON/YAML data, localization files, and custom resource types.

Implement:
- AssetManager
- typed asset handles
- cache policies
- reference-aware or explicit lifetime management where appropriate
- preload groups
- async/background loading with main-thread handoff for Pygame objects
- loading progress
- hot reload in development
- missing-asset fallback policy
- asset validation
- dependency tracking
- pack/archive abstraction
- import hooks
- asset metadata
- content hashing

Do not claim that arbitrary Pygame objects are thread-safe. Background workers should load/process data where safe and transfer final Pygame resource creation to the main thread.

ITERATION 2: test duplicate loads, hot reload while assets are in use, failed loads, corrupted files, cache invalidation, scene transitions, and long-running memory behavior.

ITERATION 3: add asset dependency graphs, build-time asset validation, release asset manifests, compression/packing interface, and CLI inspection tools.
```

# 7. MODULE 05 — UI Framework & Design System

```text
Build a retained-mode UI framework that feels like a miniature UI toolkit rather than unrelated widgets.

Core:
- UIElement tree
- layout system
- anchors, margins, padding
- constraints and responsive sizing
- clipping
- focus management
- keyboard/controller navigation
- pointer hit testing
- event routing/capture/bubble model
- z-order
- animation hooks
- accessibility metadata
- theme/style inheritance

Widgets:
Button, Label, RichText, Image, Panel, ScrollView, ListView, Grid, Stack, Flex-like layout, Slider, Toggle, Checkbox, RadioGroup, Dropdown, TextInput, Tabs, Tooltip, Modal, Toast, ProgressBar, HealthBar, ManaBar, StaminaBar, Minimap, InventoryUI, DialogueBox, QuestLog, SkillTree, RadialMenu, context menu, loading screen, settings screen, debug console UI.

Add state-driven styling: normal/hover/pressed/focused/disabled/error/selected.

ITERATION 2: test resize, nested layouts, focus traps, keyboard navigation, controller navigation, text overflow, long strings, missing fonts, DPI/display scaling, modal stacking, and event leakage.

ITERATION 3: add UI inspector, declarative UI data format, theme export/import, localization-aware layout checks, and visual regression tests.
```

# 8. MODULE 06 — Input, Controls & Device Abstraction

```text
Implement action-based input independent from raw keyboard/mouse events.

Build:
- InputMap
- action and axis abstractions
- keyboard/mouse/gamepad support
- multiple controllers
- deadzones
- analog curves
- key rebinding
- input contexts (gameplay/menu/chat/editor)
- input buffering
- press/release/held semantics
- gesture/combo detector
- configurable accessibility alternatives
- virtual touch controls for future mobile ports

Expose frame-safe polling and event-driven hooks without forcing either style.

Add device hot-plugging and controller identification where supported by Pygame.

ITERATION 2: test simultaneous devices, rebinding while input is active, lost controller events, focus changes, paused menus, duplicate bindings, and high-frequency mouse motion.

ITERATION 3: add control presets, import/export of keymaps, per-player mappings, input recording/replay hooks, and accessibility profiles.
```

# 9. MODULE 07 — Animation, Tweening & State Animation

```text
Build a reusable animation layer.

Implement:
- AnimationController
- animation states and transitions
- sprite-sheet/frame animation
- frame timing
- animation blending where practical for 2D
- frame markers/events
- Tween engine
- easing functions
- sequence/parallel/chain operations
- cancellation
- pause/time-scale support
- callbacks that are lifecycle-safe
- simple 2D skeletal/bone abstraction as an optional advanced feature

Make animation data serializable.

ITERATION 2: attack cancellation races, object destruction during callbacks, zero-duration tweens, huge frame delta, looped animations, and state transition recursion.

ITERATION 3: add animation debugging, timeline visualization hooks, hot reload of animation definitions, and editor integration contracts.
```

# 10. MODULE 08 — Physics, Collision & Queries

```text
Implement lightweight arcade/2D physics primitives while keeping Pymunk integration optional.

Build:
- PlatformerBody
- TopDownBody
- BouncyBody
- Collider shapes
- collision layers/masks
- triggers
- spatial hash/grid broad phase
- raycast/segment queries
- overlap queries
- impulse/knockback
- grounded/wall/ceiling sensors
- continuous-collision helper for fast projectiles where practical
- collision manifolds/contact information

Define deterministic collision ordering where possible.

Support simple static geometry and efficient queries for large numbers of objects.

ITERATION 2: test tunneling, corner collisions, stacked objects, large worlds, moving platforms, triggers, disabled colliders, layer changes during runtime, and broad-phase stale entries.

ITERATION 3: add physics debug draw integration, contact event diagnostics, benchmark suite, optional Pymunk bridge, and deterministic simulation hooks.
```

# 11. MODULE 09 — Camera & Viewport System

```text
Implement Camera2D as a reusable viewport system.

Features:
- follow target
- smoothing
- deadzone
- look-ahead
- bounds/clamping
- zoom
- rotation if supported by renderer policy
- camera shake
- trauma-based shake
- screen-space vs world-space layers
- camera regions/volumes
- split-screen support
- viewport management
- cinematic/cutscene paths with easing

Make camera behavior independent from specific player classes.

ITERATION 2: test teleports, target deletion, level bounds smaller than viewport, zoom extremes, resize, pause, camera stacking, and nested scene transitions.

ITERATION 3: add camera volumes, priority blending, debug overlays, recording/export of camera paths, and editor hooks.
```

# 12. MODULE 10 — Scenes, States & Application Flow

```text
Build SceneManager with real lifecycle semantics.

Support:
- register/push/pop/switch/replace
- scene stack
- overlays such as pause menus
- scene loading states
- transitions: fade, slide, wipe, iris, pixel dissolve
- SceneData/context passing
- persistent objects/services
- scene-local event cleanup
- asynchronous/preloading hooks
- loading screen API

Define a safe sequence for enter/update/render/exit/dispose.

ITERATION 2: test nested transitions, switching during events, switching while loading, scene initialization failure, repeated push/pop, persistent-object duplication, and exceptions during exit.

ITERATION 3: add scene dependency manifests, async asset prefetch, transition interruption policy, scene performance metrics, and a scene-flow diagram/export tool.
```

# 13. MODULE 11 — World, Tilemaps, Procedural Generation & Streaming

```text
Build yggame.world as a general 2D world framework.

Support:
- Tilemap loading from common structured formats such as Tiled JSON/TMX through adapters
- tile layers
- object layers
- collision layer generation
- tile metadata
- auto-tiling
- Wang/bitmask strategies
- chunking
- world streaming
- procedural generation utilities
- seeded generation
- biome/region concepts
- dungeon generators
- caves via cellular automata
- noise-based terrain
- BSP generation
- world coordinate helpers
- world-to-tile and tile-to-world conversion

Do not make procedural generation mandatory.

ITERATION 2: test massive maps, chunk boundaries, seam correctness, reloads, deterministic seeds, missing tiles, malformed maps, and collision synchronization.

ITERATION 3: add world streaming metrics, chunk caches, editor preview hooks, procedural-generation snapshots, and reproducible bug reports containing seeds/configuration.
```

# 14. MODULE 12 — VFX, Particles & Screen Effects

```text
Build a data-driven VFX system.

Implement:
- ParticleSystem
- emitters: point, circle, cone, line, rectangle
- velocity/acceleration/drag
- lifetime
- scale/rotation/alpha curves
- sprite or procedural particle modes
- color/opacity curves
- burst and continuous modes
- particle pooling
- trails
- hitsparks
- screen shake hooks
- flash/fade effects
- preset serialization

Provide production presets for fire, smoke, rain, snow, dust, sparks, magic, impact, healing, level-up, muzzle flash, and environment effects without hardcoding game-specific logic.

ITERATION 2: benchmark 1k/10k/50k particles, test pool exhaustion, emitter destruction, long-lived effects, and alpha/format issues.

ITERATION 3: add live particle inspector, preset editor API, deterministic seed option, performance budget warnings, and screenshot-safe rendering.
```

# 15. MODULE 13 — Audio, Music & Sound Design System

```text
Build an AudioManager around Pygame's audio facilities with clean abstractions.

Implement:
- master/music/SFX/voice buses
- per-channel controls
- music playlist
- crossfade
- fade in/out
- sound pool/anti-spam
- priority-based sounds
- positional 2D audio
- listener position
- distance attenuation
- stereo pan approximation
- ambient loops
- music state transitions
- pause/resume semantics
- audio device failure recovery where feasible
- settings persistence

Define asset lifetime and cleanup rules.

ITERATION 2: test repeated play calls, channel exhaustion, missing files, audio shutdown/reinit, pause/unpause, scene changes, rapid music transitions, and device errors.

ITERATION 3: add mixer diagnostics, audio event hooks, data-driven sound sets, random variation/pitch abstraction where supported, and editor preview interfaces.
```

# 16. MODULE 14 — Items, Inventory, Equipment, Crafting & Economy

```text
Build a data-driven gameplay-item subsystem.

Implement:
- Item definitions
- IDs and metadata
- rarity tiers
- stackability
- inventory containers
- slot rules
- equipment slots
- stat modifiers
- durability
- consumables
- item actions
- crafting recipes
- recipe unlocks
- loot tables
- weighted random selection with deterministic seeds
- vendor/shop interfaces
- currency abstraction

Keep backend logic separate from InventoryUI.

Add validation so broken item definitions are caught before runtime.

ITERATION 2: attack duplicated item IDs, negative quantities, overflow, invalid recipes, save/load of inventories, equipment replacement, and deterministic loot.

ITERATION 3: add item query/filter APIs, tag-based compatibility, serialization versioning, modded item namespaces, and economy test fixtures.
```

# 17. MODULE 15 — Dialogue, Narrative, Quests & Cutscenes

```text
Build a narrative framework that allows writers to author content without changing Python.

Implement:
- DialogueTree
- branching choices
- conditions
- variables/flags
- item/state checks
- speaker metadata
- portraits
- localization keys
- DialogueParser with a small readable script syntax
- QuestSystem
- objectives and stages
- reward triggers
- quest dependencies
- cutscene command sequences
- move/show/hide/play animation/play sound/wait/camera/dialogue commands
- skip/fast-forward rules

Build save-safe narrative state.

ITERATION 2: test circular dialogue graphs, missing nodes, invalid conditions, save/load in the middle of a conversation, skipping cutscenes, localization expansion, and interrupted scenes.

ITERATION 3: add dialogue validation CLI, graph visualization/export, narrative test runner, branching coverage report, and editor hooks.
```

# 18. MODULE 16 — AI, Behavior Trees, State Machines & Perception

```text
Build generic AI building blocks rather than one hardcoded enemy system.

Implement:
- generic finite state machine
- Behavior Tree nodes
- sequence/selector/parallel/condition/action/decorator nodes
- blackboard
- steering behaviors
- seek/flee/wander/arrive
- obstacle avoidance
- flocking
- perception: vision cone, hearing radius, proximity checks
- threat/target selection helpers
- navigation interface

Design AI updates to be budgetable and schedulable so large NPC counts do not consume the entire frame.

ITERATION 2: test behavior tree loops, node failures, missing blackboard keys, destroyed targets, perception edge cases, and thousands of agents.

ITERATION 3: add AI profiler, behavior trace recording, deterministic tick mode, debug visualization, and an optional AI decision budget scheduler.
```

# 19. MODULE 17 — Pathfinding & Navigation

```text
Build a navigation subsystem integrated with world/tilemap data.

Implement:
- A* on grid graphs
- configurable movement costs
- diagonal movement rules
- blocked/occupied nodes
- dynamic obstacle updates
- waypoint/path objects
- smoothing hooks
- flow-field pathfinding
- navigation interface for AI
- optional graph adapters for non-grid worlds

Paths must be cancellable and safely invalidated when maps change.

ITERATION 2: test no-path cases, huge maps, changing obstacles, diagonal corner cutting, concurrent requests, and stale cached paths.

ITERATION 3: add pathfinding caches, async job hooks, benchmark suite, debug visualization, and deterministic path tests.
```

# 20. MODULE 18 — Networking & Multiplayer

```text
Build multiplayer as an optional subsystem with explicit authority models.

Implement abstractions for:
- LAN discovery
- client/server sessions
- lobby/room codes
- connection state
- player identity
- packet/message envelopes
- serialization/versioning
- reliable/unreliable channels
- sequencing
- heartbeat/timeouts
- state synchronization
- snapshot interpolation
- client prediction hooks
- reconciliation hooks
- basic rollback primitives where appropriate

Do not pretend a local library is a secure production server by default. Document trust boundaries and recommend authoritative server logic for competitive gameplay.

Add rate limiting, malformed-message rejection, protocol version checks, maximum packet/message sizes, and connection timeouts.

ITERATION 2: simulate packet loss, duplication, reordering, latency, disconnects, reconnects, malformed packets, clients sending impossible state, and version mismatch.

ITERATION 3: add network simulator tests, bandwidth metrics, packet tracing, deterministic rollback test fixtures, lobby service interface, and server headless mode.
```

# 21. MODULE 19 — Save/Load, Profiles, Replays & Deterministic State

```text
Build a durable state persistence subsystem.

Implement:
- SaveManager
- multiple save slots
- profile metadata
- schema versioning
- migration system
- atomic writes
- corruption detection
- backup rotation
- autosave policies
- save-on-scene-change hooks
- optional cloud-save adapter interface
- replay/event recording interface
- deterministic simulation snapshot hooks

Never trust save files as inherently safe or valid. Validate data before applying it.

ITERATION 2: test interrupted writes, corrupted files, version migration, unknown fields, missing fields, disk full errors, concurrent saves, autosave during transitions, and large save files.

ITERATION 3: add save inspection CLI, migration dry-run mode, replay metadata, checksum diagnostics, save compatibility tests, and optional encrypted adapter interface with clear caveats.
```

# 22. MODULE 20 — Localization, Fonts & Accessibility

```text
Build internationalization and accessibility as first-class infrastructure.

Implement:
- translation keys
- language switching at runtime
- pluralization abstraction
- parameter interpolation
- fallback language
- missing-key diagnostics
- font fallback chains
- RTL-aware layout hooks
- glyph coverage checks
- locale-aware number/date formatting where appropriate
- accessibility metadata
- scalable UI text
- color-contrast validation hooks
- controller/keyboard alternative interactions
- reduced motion setting
- screen-flash intensity/reduction hooks

Do not hardcode visible strings inside components.

ITERATION 2: test missing translations, long translations, CJK/Devanagari/Arabic glyph coverage, right-to-left layout assumptions, font loading failures, and accessibility settings.

ITERATION 3: add localization linter, translation extraction tool, pseudo-localization mode, UI overflow test mode, and accessibility documentation.
```

# 23. MODULE 21 — Editor, Inspector & Developer Tools

```text
Build an optional in-game and external-tooling layer.

Implement:
- LiveInspector
- entity/object property inspection
- runtime toggles
- scene inspector
- hierarchy view
- event monitor
- asset inspector
- particle editor contract
- tilemap preview/hot reload
- console commands
- spawn/despawn helpers
- teleport
- collision debug toggle
- AI debug toggle
- network debug panel
- performance graphs

Developer commands must be disabled or clearly gated in release builds.

Provide a command registry with typed arguments, autocomplete, help text, and safe error reporting.

ITERATION 2: test tool shutdown, release-build behavior, stale references, malformed commands, editing an object while it is being destroyed, and hot reload races.

ITERATION 3: add remote-debugging interface as an opt-in advanced feature, inspector snapshots, searchable object hierarchy, and JSON export for bug reports.
```

# 24. MODULE 22 — Debugging, Profiling, Telemetry & Crash Diagnostics

```text
Build a production observability subsystem.

Implement:
- structured Logger
- levels and categories
- rotating file logs
- in-game log console
- FPS/frame-time overlay
- frame-time graph
- draw-call/render metrics where available
- memory/resource counters where measurable
- per-system profiler
- scoped timers
- counters/gauges
- event tracing
- crash context collection
- last-N-event ring buffer
- bug-report export

Telemetry must be opt-in and privacy-conscious. No network telemetry by default.

ITERATION 2: benchmark instrumentation overhead, test logger recursion, log flooding, file permission failures, crash-handler reentry, and profiler memory use.

ITERATION 3: add performance budgets, regression benchmark reports, profiling snapshots, and automatic development-mode diagnostics.
```

# 25. MODULE 23 — Plugin, Extension & Modding System

```text
Build a plugin ecosystem without making the core unstable.

Define:
- plugin manifest
- semantic version compatibility
- plugin metadata
- dependency declarations
- capability declarations
- plugin lifecycle
- registration APIs
- component registration
- CLI command registration
- asset provider registration
- editor tool registration
- theme registration
- custom event definitions

Separate trusted in-process plugins from untrusted mods. Python code loaded into the same interpreter is not a strong security sandbox. For untrusted content, define safer data-only mod formats or process isolation.

Add namespacing for modded assets/items/components.

ITERATION 2: test duplicate plugin IDs, incompatible versions, dependency cycles, partial plugin failures, unload limitations, and registration cleanup.

ITERATION 3: add plugin discovery CLI, plugin validation, lockfile support, compatibility diagnostics, example plugin, and mod-pack metadata standard.
```

# 26. MODULE 24 — CLI, Project Scaffolding & Developer Experience

```text
Build a professional command-line experience.

Commands should include concepts such as:
- yggame new
- yggame doctor
- yggame run
- yggame test
- yggame profile
- yggame validate-assets
- yggame validate-dialogue
- yggame inspect-save
- yggame pack
- yggame clean
- yggame plugin
- yggame version

Project templates:
- minimal
- platformer
- top-down
- RPG
- shooter
- puzzle
- multiplayer client/server
- ECS demo

Generated projects must actually run.

Add environment diagnostics: Python version, Pygame-CE version, OS, display capability, optional dependencies, asset paths, and common configuration mistakes.

ITERATION 2: test clean-machine bootstrap, missing optional dependencies, invalid project paths, Windows/macOS/Linux path differences, and partially generated projects.

ITERATION 3: add template versioning, upgrade/migration tooling, project health score, and interactive troubleshooting.
```

# 27. MODULE 25 — Testing, QA, CI & Benchmarking

```text
Build a real quality system for the whole library.

Use pytest-based tests with categories:
- unit
- integration
- regression
- serialization compatibility
- deterministic simulation
- networking simulation
- asset validation
- localization
- plugin compatibility
- visual regression where practical
- performance benchmarks

Create fixtures for clocks, event buses, assets, fake renderers, fake network transports, deterministic RNG, and temporary save directories.

Add property-based testing where it gives strong value for parsers, serialization, pathfinding, inventory quantities, event behavior, and data validators.

Add benchmark suites for hot systems.

Define CI quality gates: formatting, linting, typing, tests, coverage threshold, package build, documentation build, example smoke tests.

ITERATION 2: deliberately inject failures and verify tests catch them.

ITERATION 3: add flaky-test detection, benchmark regression thresholds, compatibility matrix tests, and release-candidate smoke testing.
```

# 28. MODULE 26 — Documentation, Examples & Learning Experience

```text
Build documentation as part of the product, not as an afterthought.

Create:
- quickstart
- architecture guide
- API reference
- module guides
- recipes
- troubleshooting
- performance guide
- networking guide
- plugin/modding guide
- migration guide
- contributing guide
- security model
- compatibility matrix

Every public component must have:
- what it does
- minimum example
- customization example
- integration example
- common mistakes
- lifecycle notes
- performance notes
- thread-safety/main-thread notes when relevant

Create a runnable example for every major component family and several complete sample games.

ITERATION 2: have a developer unfamiliar with internals follow the quickstart and identify friction points.

ITERATION 3: add search-friendly cross-links, generated API docs, interactive examples where practical, and a “choose the right subsystem” guide.
```

# 29. MODULE 27 — Packaging, Distribution & Release Engineering

```text
Make yggame distributable as a professional Python package.

Implement:
- pyproject.toml
- optional dependency groups
- wheel/sdist builds
- package metadata
- semantic versioning
- changelog generation
- deprecation policy
- compatibility policy
- license/notice files
- release checks
- reproducible build considerations
- source distribution tests
- wheel installation smoke tests
- documentation publishing pipeline

Target platforms should be validated independently rather than assumed.

Define public API exports carefully and keep internal modules private.

ITERATION 2: build from a clean environment, install wheel without repository access, test optional extras, and verify package data inclusion.

ITERATION 3: add release candidate workflow, API compatibility report, package-size report, example-game smoke tests after installation, and rollback/release checklist.
```

# 30. MODULE 28 — Security, Safe Runtime & Content Validation

```text
Build a security/reliability layer appropriate for a Python game framework.

Focus on:
- validating external data
- safe parsing
- path traversal prevention in asset loading/packing
- limits on file size and decompression expansion where relevant
- malformed network packet handling
- authentication hooks for multiplayer adapters
- rate limiting
- plugin trust levels
- release-build developer-command gating
- crash-safe persistence
- secret/config separation
- avoiding unsafe deserialization of arbitrary Python objects

Do not use pickle for untrusted save/network/plugin data.

Document the threat model clearly: local game execution, modding, multiplayer clients, server operators, asset packs, and development tooling are different trust domains.

ITERATION 2: attack parsers, asset paths, save files, plugin manifests, and network messages with hostile inputs.

ITERATION 3: add automated security tests, dependency audit hooks, secret-scanning guidance, and a SECURITY.md-style process.
```

# 31. MODULE 29 — Sample Games, Integration & Product Validation

```text
Prove the framework works by building complete games from the library rather than examples that merely demonstrate isolated widgets.

Build at minimum:
1. Platformer sample
2. Top-down action sample
3. RPG sample with inventory/dialogue/quests/save
4. Shooter sample with particles/audio/AI
5. Local multiplayer sample
6. Procedural dungeon sample
7. ECS performance sandbox
8. UI showcase
9. Editor/dev-tools showcase

Each sample must use public yggame APIs as a real external user would.

No sample should import private internals unless the public API genuinely lacks something. When a sample requires a private API, treat it as an API design defect and evaluate whether to promote a stable public interface.

ITERATION 2: pretend the samples are maintained by a separate team. Find coupling, hidden assumptions, and undocumented APIs.

ITERATION 3: use samples as integration regression tests, performance baselines, documentation sources, and release smoke tests.
```

# 32. MODULE 30 — Final Integration, Compatibility & “100% Product” Gate

```text
Act as the final chief architect and release manager.

Do not add features blindly. Audit the entire repository against the intended product.

Create a capability matrix covering every module and every cross-cutting contract:
- Events
- Assets
- Scene lifecycle
- Config
- Rendering
- Input
- Serialization
- Logging
- Debugging
- Testing
- Plugins
- Documentation
- CLI

Check every major subsystem for:
- public API consistency
- naming consistency
- lifecycle consistency
- error consistency
- serialization/versioning consistency
- dependency direction
- headless testability
- performance hooks
- accessibility hooks
- localization readiness
- editor integration
- plugin/extensibility hooks
- release readiness

Build an integration test suite that creates a real game context and exercises a realistic flow:
boot -> load assets -> create scene -> input -> physics -> AI -> animation -> VFX -> audio -> UI -> save -> scene transition -> reload -> debug/profile -> clean shutdown.

Then perform a final adversarial review:
- What would break after 8 hours of runtime?
- What would break on a low-end machine?
- What would break if a user never reads the documentation?
- What would break if a plugin fails?
- What would break if a save is corrupted?
- What would break when a window is resized?
- What would break when assets are missing?
- What would break during network packet loss?
- What feature is still only “demo-quality”?
- Which public API is likely to create long-term technical debt?

Fix the most important issues before declaring the release ready.
```

---

# 33. CROSS-CUTTING FEATURES THAT SHOULD EXIST ACROSS THE WHOLE PROJECT

## A. Unified service/context layer
Every subsystem should be able to access shared services through an explicit context. Avoid random singleton dependencies.

## B. Unified event taxonomy
Define stable built-in event categories such as:
- lifecycle
- input
- scene
- collision
- damage/combat
- inventory
- dialogue/quest
- audio
- asset loading
- networking
- save/load
- debug/tooling

Allow user-defined events without namespace collisions.

## C. Unified theming
One Theme/Style object should be able to configure the UI globally. Add light/dark themes, high-contrast mode, color-blind-friendly palettes, reduced motion, and typography settings.

## D. Unified serialization
A common versioned serialization protocol should be reusable by save files, replay metadata, component state, item data, dialogue state, and network messages where appropriate.

## E. Unified diagnostics
Every major subsystem should expose optional diagnostics without forcing logging/profiling overhead in production.

## F. Unified lifecycle
Every stateful system should have clear initialization, activation, update, render-if-applicable, deactivate, and dispose semantics.

## G. Unified data validation
Definitions loaded from JSON/TOML/YAML/custom files should be validated before use. Prefer clear schema errors with file path + field + expected type/value.

## H. Unified compatibility strategy
Version public data formats and APIs. Deprecate rather than silently changing behavior.

---

# 34. NEW “BEYOND THE ORIGINAL IDEA” FEATURES

These are deliberate upgrades beyond the original 20-module concept.

### Deterministic simulation mode
Useful for replays, rollback networking, debugging, and reproducible bugs. Provide deterministic RNG, injectable clocks, controlled system ordering, and state snapshots.

### Replay/debug recording
Capture inputs/events and optionally snapshots so developers can reproduce bugs or show gameplay.

### Performance budget system
Allow a project to define budgets such as:
- max frame time
- max particle count
- max AI time
- max asset load time
- max memory target

Warn in development when budgets are exceeded.

### Visual regression testing
Render known scenes and compare outputs with tolerances. This is particularly valuable for UI, rendering, camera, animation, and particle regressions.

### Data validation CLI
Scan all game content before launch and fail early for invalid references, duplicate IDs, missing assets, broken dialogue links, impossible recipes, missing translations, and malformed tilemaps.

### Project health command
A command such as `yggame doctor` should report dependency status, configuration problems, asset-path problems, platform issues, optional feature availability, and obvious project mistakes.

### Reproducible bug bundle
Provide a development-only export that stores:
- yggame version
- Python/Pygame versions
- platform
- relevant config
- deterministic seed
- recent events
- last scene
- performance summary
- relevant save snapshot metadata
- logs

Never automatically include secrets.

### Headless server mode
For multiplayer games, allow a server process without a graphical window, using the same authoritative simulation APIs where possible.

### Hot reload
Support development hot reload for assets, selected data definitions, localization, tilemaps, particle presets, themes, and optionally dialogue. Always define when state is recreated versus preserved.

### Mod namespaces
Give mods stable namespaces for assets, items, entities, recipes, dialogue IDs, translations, and plugin registrations.

### Compatibility test matrix
Test supported combinations of Python/Pygame-CE/platforms and clearly declare what is supported.

### Example-driven API quality
Every major API must be proven through a real sample project.

---

# 35. “SELF-IMPROVE AFTER EVERY MODULE” MINI PROMPT

Paste this after completing every individual module:

```text
The module is implemented. Do not stop.

Now perform a formal post-module upgrade pass.

1. Read every new and modified file.
2. List the 10 most likely failure modes.
3. List the 10 most likely developer-experience problems.
4. List the 10 most likely performance problems.
5. List the 10 most likely integration problems with other yggame modules.
6. Pick the 3 highest-value fixes/features from those lists.
7. Implement those 3 upgrades.
8. Add or improve tests for each.
9. Update documentation and examples.
10. Re-run the full relevant test suite.
11. Check the public API for accidental complexity.
12. Check whether the new feature created duplicate abstractions.
13. Check whether the feature should expose editor/CLI/debug hooks.
14. Check serialization/versioning implications.
15. Check accessibility/localization implications for user-facing features.
16. Check release/package implications.

Finally answer:
- What became better?
- What hidden bug was found?
- What new capability was added?
- What technical debt remains?
- What is the most logical next module integration?
```

---

# 36. GLOBAL “BEAST MODE” REVIEW PROMPT

Use this after every 5–6 modules, not after every tiny commit.

```text
You are now the principal engineer reviewing yggame as if it were a serious open-source game framework approaching its first public release.

Do not assume the current architecture is correct just because it works.

Inspect the last 5–6 modules together and identify:
1. duplicated abstractions
2. inconsistent naming
3. inconsistent lifecycle behavior
4. inconsistent error handling
5. circular dependencies
6. hidden global state
7. performance regressions
8. poor public APIs
9. serialization incompatibilities
10. documentation gaps
11. missing tests
12. missing editor/debug integration
13. plugin/extensibility problems
14. accessibility/localization oversights
15. release/package problems
16. security weaknesses
17. opportunities for useful shared infrastructure

Then:
- refactor only where there is measurable architectural value
- preserve backwards compatibility where reasonable
- add missing shared utilities/contracts
- update documentation
- add regression tests
- run quality checks

Do not add random features merely to make the codebase larger. Optimize for developer value, reliability, maintainability, and composability.
```

---

# 37. RECOMMENDED IMPLEMENTATION ORDER

### Foundation
00 Architecture
01 Core
02 ECS

### Runtime
03 Rendering
04 Assets
05 UI
06 Input
07 Animation
08 Physics
09 Camera
10 Scenes

### World/gameplay
11 World
12 VFX
13 Audio
14 Inventory
15 Dialogue/Quests
16 AI
17 Navigation

### Advanced platform
18 Networking
19 Save/Replays
20 Localization/Accessibility
21 Editor
22 Debug/Profiling
23 Plugins/Modding
24 CLI/Templates

### Productization
25 QA/CI/Benchmarks
26 Documentation/Examples
27 Packaging/Release
28 Security
29 Sample Games
30 Final Integration

---

# 38. DEFINITION OF DONE FOR EVERY MODULE

A module is not “done” when the code runs once.

It is done when:

- production path implemented
- public API defined
- invalid input behavior defined
- lifecycle defined
- tests exist
- integration test exists
- example exists
- docs exist
- performance concerns considered
- error handling exists
- optional dependencies are explicit
- serialization implications reviewed
- debug/inspection hooks considered
- iteration 2 adversarial review completed
- iteration 3 product upgrade completed
- no placeholder implementation remains
- CI passes
- public API exports are intentional

---

# 39. 100% PRODUCT VISION

The finished yggame should feel like a cohesive mini-engine ecosystem built on Pygame-CE, not a random utility package.

A developer should be able to do something conceptually like:

```python
from yggame import Game
from yggame.scenes import Scene
from yggame.ui import HealthBar, Button
from yggame.physics import PlatformerBody
from yggame.audio import AudioManager

app = Game.create("My Game")
app.run()
```

and then progressively opt into more systems without being forced to adopt them all.

The strongest differentiator should be composability:

EventBus + Context + Assets + Scenes + Render + UI + Input + Physics + Animation + VFX + Audio + World + AI + Inventory + Narrative + Save + Networking + Tools + Testing + Plugins + CLI + Documentation.

The goal is not simply “1–2 lakh lines of code.” The goal is a framework where every extra line creates a reusable capability, a stable contract, a testable subsystem, or meaningful developer leverage.

That is the standard to use when deciding whether a proposed feature belongs in yggame.
