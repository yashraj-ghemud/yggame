# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Command-line helpers for starting and diagnosing yggame projects."""

from __future__ import annotations

import argparse
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="yggame", description="yggame development utilities")
    subparsers = parser.add_subparsers(dest="command", required=True)
    new = subparsers.add_parser("new", help="create a minimal game project")
    new.add_argument("name")
    new.add_argument("--path", type=Path, default=Path.cwd())
    subparsers.add_parser("doctor", help="check optional integrations")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "doctor":
        print("yggame core: available")
        for package in ("pygame", "pymunk", "websockets", "babel"):
            try:
                __import__(package)
            except ImportError:
                print(f"{package}: optional dependency not installed")
            else:
                print(f"{package}: available")
        return 0
    if args.command == "new":
        root = args.path / args.name
        root.mkdir(parents=True, exist_ok=False)
        (root / "main.py").write_text(
            "from yggame import Game\n\n\nif __name__ == '__main__':\n    Game().run(frames=1)\n",
            encoding="utf-8",
        )
        (root / "README.md").write_text(f"# {args.name}\n\nA yggame project.\n", encoding="utf-8")
        print(f"created {root}")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
