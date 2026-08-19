# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Command-line launcher for the five yggame demos."""

from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass

from .base import DemoCommand, DemoGame, DemoResult, command_script


@dataclass(frozen=True, slots=True)
class DemoSpec:
    key: str
    title: str
    category: str
    description: str
    factory: Callable[[int], DemoGame]


_REGISTRY: dict[str, DemoSpec] = {}


def register(spec: DemoSpec) -> DemoSpec:
    if spec.key in _REGISTRY:
        raise ValueError(f"duplicate demo key: {spec.key}")
    _REGISTRY[spec.key] = spec
    return spec


def all_specs() -> tuple[DemoSpec, ...]:
    return tuple(sorted(_REGISTRY.values(), key=lambda item: item.key))


def load_specs() -> None:
    if _REGISTRY:
        return
    from . import bastion, emberdeep, missing_signal, neon_swarm, skybound_runner

    register(
        DemoSpec(
            "skybound",
            "Skybound Runner",
            "platformer action",
            "Run, jump, collect relics, and reach the beacon.",
            skybound_runner.SkyboundRunner,
        )
    )
    register(
        DemoSpec(
            "swarm",
            "Neon Swarm",
            "top-down arena survival",
            "Survive escalating enemy waves while upgrading your weapon.",
            neon_swarm.NeonSwarm,
        )
    )
    register(
        DemoSpec(
            "emberdeep",
            "Emberdeep",
            "roguelike dungeon crawler",
            "Explore a seeded dungeon, loot equipment, and descend.",
            emberdeep.Emberdeep,
        )
    )
    register(
        DemoSpec(
            "bastion",
            "Last Bastion",
            "tower-defense strategy",
            "Build a defense grid and hold back scheduled enemy waves.",
            bastion.LastBastion,
        )
    )
    register(
        DemoSpec(
            "signal",
            "The Missing Signal",
            "narrative detective RPG",
            "Investigate clues, make dialogue choices, and close the case.",
            missing_signal.MissingSignal,
        )
    )


def create(key: str, seed: int) -> DemoGame:
    load_specs()
    try:
        return _REGISTRY[key].factory(seed)
    except KeyError as exc:
        raise KeyError(f"unknown demo: {key}") from exc


def run_script(
    game: DemoGame, commands: tuple[DemoCommand, ...], *, verbose: bool = True
) -> tuple[DemoResult, ...]:
    results: list[DemoResult] = []
    for command in commands:
        result = game.step(command)
        results.append(result)
        if verbose:
            print(
                f"[{result.step:02d}] {result.message} | "
                f"status={result.status} score={result.score}"
            )
        if result.status in {"won", "lost"}:
            break
    return tuple(results)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run one of the yggame demonstration games")
    parser.add_argument("game", nargs="?", help="demo key, or 'list'")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--steps", type=int, default=12)
    parser.add_argument("--commands", help="comma-separated scripted commands")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--board", action="store_true", help="print the final text board")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    load_specs()
    if args.game in {None, "list"}:
        for spec in all_specs():
            print(f"{spec.key:10} {spec.title:20} [{spec.category}] — {spec.description}")
        return 0
    game = create(args.game, args.seed)
    commands = command_script(args.commands, game.default_commands()[: max(0, args.steps)])  # type: ignore[attr-defined]
    run_script(game, commands, verbose=not args.quiet)
    if args.board:
        print(game.render_text())
    print(game.summary())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
