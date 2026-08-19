# yggame

**yggame** is a composable Python component library for building 2D games with Pygame-CE. It provides a headless-first runtime core, optional rendering adapters, scene management, input mapping, animation, collision helpers, UI primitives, inventory, dialogue, quests, AI, pathfinding, saves, and asset caching.

The project is being built as a production-oriented foundation. It intentionally favors **tested contracts and useful implementations over generated line count**. Large systems such as networking, skeletal animation, advanced lighting, and editor windows will be added behind stable interfaces rather than shipped as fragile placeholders.

## Developer credit

**Developer and maintainer:** Yashraj Sachin Ghemud

This project, its public APIs, tests, examples, and release configuration are maintained under the name **Yashraj Sachin Ghemud**. Please retain this attribution when redistributing the project.

## Installation

```bash
pip install yggame[dev]
# Add Pygame when building a graphical game:
pip install yggame[pygame]
```

The core package can be imported without Pygame, a display, or an audio device. This makes content validation, save migrations, simulations, and automated tests safe in CI and server environments.

## Quick start

```python
from yggame import Game
from yggame.core import BaseSystem


class Simulation(BaseSystem):
    def update(self, delta: float) -> None:
        super().update(delta)
        # Advance gameplay here using a fixed simulation delta.

    def draw(self, target, interpolation: float = 0.0) -> None:
        pass


if __name__ == '__main__':
    game = Game(fixed_delta=1 / 60)
    game.add_system(Simulation())
    game.run(frames=1)
```

## Example composition

```python
from yggame.core import Rect, Vec2
from yggame.input import InputMap
from yggame.physics import CollisionGrid, PlatformerBody
from yggame.ui import HealthBar

controls = InputMap()
controls.bind('move_left', 'keyboard:a')
controls.bind('move_right', 'keyboard:d')
controls.bind('jump', 'keyboard:space')

world = CollisionGrid(80, 30, tile_size=32)
player = PlatformerBody(Rect(96, 128, 24, 40))
health = HealthBar(maximum=100)
```

## Public subsystem map

| Namespace | Responsibility | Headless by default |
| --- | --- | --- |
| `yggame.core` | Game loop, context, events, timing, ECS, geometry, config, pooling | Yes |
| `yggame.render` | Layered render queue and viewport transforms | Queue yes; drawing adapter optional |
| `yggame.scenes` | Scene registry, stack navigation, transitions | Yes |
| `yggame.camera` | Follow camera, bounds, zoom, screen shake | Yes |
| `yggame.physics` | Collision grids, spatial hash, raycasts, movement bodies | Yes |
| `yggame.ui` | Retained UI tree and common widgets | Yes |
| `yggame.anim` | Tweens and frame animation state machines | Yes |
| `yggame.inventory` | Items, stacks, equipment, crafting, loot | Yes |
| `yggame.dialogue` | Dialogue trees, choices, quests | Yes |
| `yggame.ai` | FSM and behavior trees | Yes |
| `yggame.world` | A* and flow fields | Yes |
| `yggame.save` | Versioned save files and autosave | Yes |
| `yggame.assets` | Cached asset loading and hot reload | Yes |

## Quality policy

Every public subsystem should have deterministic unit tests, explicit error behavior, and at least one runnable example before being treated as stable. Optional integrations must be isolated so importing the package never requires them. Data files carry schema versions, and public constructors prefer keyword-only extension points to reduce accidental breaking changes.

## License

MIT. See [LICENSE](LICENSE).

## Five runnable demo games

The repository includes five deterministic, headless-first demo games under `examples/yggame_demos/`. Each demo is a small but complete vertical slice rather than a disconnected API snippet: it owns gameplay state, accepts typed commands, produces a transcript result, renders a terminal board, and composes multiple yggame subsystems.

| Demo | Category | Representative yggame systems |
| --- | --- | --- |
| **Skybound Runner** | Platformer action | `PlatformerBody`, `CollisionGrid`, `Camera2D`, `Health`, particles |
| **Neon Swarm** | Top-down arena survival | `TopDownBody`, `SpatialHash`, steering agents, encounter waves, stats, status effects |
| **Emberdeep** | Roguelike dungeon crawler | BSP rooms, inventory, equipment, weighted loot, stats, recovery checkpoints |
| **Last Bastion** | Tower-defense strategy | Tilemap, A*, encounter scheduler, cooldowns, health, economy |
| **The Missing Signal** | Narrative detective RPG | Dialogue parser/session, quest system, content registry, saves, telemetry |

Run the launcher from the repository root:

```bash
python3 examples/run_demos.py list
python3 examples/run_demos.py skybound --board
python3 examples/run_demos.py swarm --steps 12 --board
python3 examples/run_demos.py emberdeep --commands 'explore,explore,fight,loot,save' --board
python3 examples/run_demos.py bastion --commands 'build 5,4,build 8,4,wait,wait' --board
python3 examples/run_demos.py signal --commands 'talk,choose 0,inspect dock,talk,choose 1,inspect frequency,travel relay,inspect blueprint,report'
```

The examples do not require a display or Pygame installation for their scripted scenarios. They are intended to be extended into graphical scenes by replacing the terminal `render_text()` implementations with yggame render queues and an optional Pygame adapter. The shared `DemoGame` protocol in `examples/yggame_demos/base.py` is deliberately small enough to use as a test seam for future graphical front ends.

## Verification

Run the complete headless quality gate with:

```bash
ruff check src tests examples
mypy src/yggame
python3 -m pytest -q
```

## Release verification

From a clean checkout, the release workflow is:

```bash
python -m pip install -e '.[dev]'
ruff check src tests examples
mypy src/yggame
python -m pytest -q
python -m build
python -m twine check dist/*
```

The package is headless-first and can be installed without Pygame. Optional integrations are available through the `pygame`, `physics`, `network`, `localization`, and `all` extras.
