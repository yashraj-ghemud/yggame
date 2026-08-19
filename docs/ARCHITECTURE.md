# yggame Architecture

## Purpose

yggame is a component library rather than a monolithic engine. Its contracts are designed so that a game can use one widget, one physics helper, or the complete runtime without adopting a specific entity model. The library is deliberately split into a **headless domain layer**, an **optional Pygame adapter layer**, and **developer tooling**.

## Design principles

| Principle | Implementation consequence |
| --- | --- |
| Headless first | Inventory, dialogue, save data, event routing, timing, ECS, AI decisions, and pathfinding must run without a display or audio device. |
| Explicit lifecycle | Objects expose predictable `start`, `update`, `draw`, and `shutdown` hooks; resources are owned and released by a context. |
| Composition over inheritance | Small protocols and data classes are preferred over deep base-class hierarchies. |
| Deterministic simulation | Fixed-step updates, injectable clocks, seeded random sources, and serializable state make replays and tests possible. |
| Optional integrations | Pygame-CE, Pymunk, websockets, and Babel are extras; importing `yggame` must not require them. |
| Stable events | Events are immutable records with a type, source, payload, timestamp, and propagation policy. |
| No hidden singleton | A `Context` can provide shared services, but every system can also be constructed directly. |
| Fail loudly at boundaries | Invalid configuration, malformed assets, and schema mismatches raise typed exceptions with actionable messages. |

## Runtime layers

```text
Application / game code
        |
        +-- scenes, gameplay components, UI, AI, inventory, dialogue
        |
        +-- context services: event bus, clock, assets, input, audio, renderer
        |
        +-- core contracts: lifecycle, geometry, serialization, diagnostics
        |
        +-- optional adapters: pygame-ce, pymunk, websockets, Babel
```

The core layer does not import Pygame. Modules that need Pygame use lazy imports and typed protocols. This keeps CI, server simulations, content validation, and save migration tests display-free.

## Update model

`Game` uses a fixed simulation step with an accumulator. A frame may render once while simulation advances zero or more fixed steps. Systems receive a `FrameContext` containing simulation time, real time, time scale, interpolation alpha, input snapshot, event bus, and diagnostics. A maximum catch-up limit prevents a stalled machine from entering a spiral of death.

## Error model

All public subsystems use exceptions derived from `YggameError`. Configuration errors, missing assets, lifecycle errors, serialization errors, and optional-dependency errors are distinguishable. Recoverable runtime events are logged and published rather than swallowed.

## Compatibility strategy

The first release targets Python 3.10+ and Pygame-CE 2.5+. Public objects are typed and documented. New behavior is added through optional keyword-only arguments, while breaking changes require a major version. Data formats carry explicit schema versions. Plugin registrations are namespaced and validated before activation.

## First vertical slice

The first implementation delivers a working platform for a small game:

1. Core context, event bus, signals, clock, fixed-step game loop, object pool, ECS, and configuration.
2. Geometry helpers, layered renderer, camera, scene manager, input map, animation tweening, and a Pygame bridge.
3. Headless inventory, dialogue, quests, save migrations, A* pathfinding, collision grid, and basic platformer/top-down movement.
4. UI primitives and gameplay widgets built on a retained-mode tree, with optional rendering.
5. Tests and examples that exercise the contracts without requiring a full game project.

Large features such as rollback networking, skeletal animation, shadow casting, and editor windows are kept behind explicit interfaces so they can mature without destabilizing the core.
