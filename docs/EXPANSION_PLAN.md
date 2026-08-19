# yggame Expansion Plan

## Baseline audit

The current release is a coherent alpha foundation with approximately 3,500 source lines across 47 Python files and 12 passing tests. It has good subsystem breadth but not yet enough depth for high-end game development. The most important gaps are not raw line count; they are production contracts around resource ownership, serialization, rendering adapters, richer UI layout, robust physics queries, content schemas, replayability, networking primitives, and sample-game infrastructure.

## Iteration policy

Each expansion pass must add at least one of the following: a public capability, a typed contract, a failure-mode test, a performance-oriented data structure, a content schema, a complete example, or documentation that makes an existing system safer to use. Generated code is acceptable only for repetitive, testable data tables; filler classes and duplicate aliases are not acceptable.

## Pass sequence

| Pass | Focus | Main deliverables |
| --- | --- | --- |
| 1 | Core depth | Resource handles, service scopes, serialization codecs, replay/input recording, diagnostics snapshots, scheduler improvements, richer configuration validation |
| 2 | Presentation | Sprite/atlas loading, text layout, color/theme system, retained UI layout constraints, focus navigation, modal/tooltip/list/grid widgets, render targets and effects interfaces |
| 3 | Simulation | Shapes/manifolds, collision layers, triggers, platformer edge cases, tilemaps/chunks, procedural generators, particle emitters, animation graphs, audio pools |
| 4 | Game data | Item schemas, stat formulas, status effects, quests, dialogue parser, localization catalogs, save migrations, deterministic RNG, behavior-tree decorators |
| 5 | Tooling/networking | Plugin discovery, CLI project templates, content validation, LAN transport interfaces, snapshots, prediction/rollback primitives, profiler reports, sample game |
| 6 | Hardening | Broad tests, import matrix, optional-dependency behavior, documentation, benchmarks, package build, API review, release notes |

## Self-questioning checklist

### Can a system be used headlessly?

If yes, keep it in the dependency-free domain layer. If no, isolate the adapter and make the error explicit when the optional dependency is missing.

### Can state be saved and replayed?

Runtime state should be represented by stable identifiers and serializable values where practical. Nondeterministic systems should accept injected random sources or clocks.

### What happens on partial failure?

Asset loading, plugin registration, save migration, network transport, and scene transitions need typed exceptions, rollback/cleanup behavior, and actionable error messages.

### Is the public API composable?

New features should accept protocols, callbacks, or data objects instead of requiring a monolithic base class. The same component should remain usable in an OOP game, ECS world, or plain-function loop.

### Is performance behavior visible?

Systems handling many entities need bounded work, stable ordering, pooling or reuse where appropriate, and diagnostics that make cost measurable instead of relying on guesses.

## Acceptance target for the next release

The next release should be materially more complete, not just larger. It should add several thousand lines of tested implementation, at least 30 new tests, at least three examples, richer API documentation, and no regression in importability, lint, type checks, or package build. The 50,000-line target should be treated as a long-term scale objective reached through multiple quality releases rather than one padded snapshot.
